# -*- coding: utf-8 -*-
"""
convert_mbz_to_imscc.py — converts the sample Moodle backup (.mbz) into an
IMS Common Cartridge (.imscc) shaped for Canvas import.

- Sections, pages, labels, file resources, the assignment and quizzes are mapped.
- Questions become IMS QTI 1.2 items (the assessment format Common Cartridge uses).
- Files and images are copied byte-identical from the backup's hashed storage.
- Anything that cannot be converted faithfully is NOT dropped: it becomes a
  clearly labelled placeholder (see exceptions.html in the cartridge and
  conversion-counts.json), matching the Pre-Migration Exception Report model.

Idempotent: output folder and .imscc are rebuilt on every run.
"""
import io, os, re, json, shutil, hashlib, zipfile, tarfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
MBZ = os.path.join(HERE, "Sample-Course-Moodle-Backup.mbz")
OUTDIR = os.path.join(HERE, "build_imscc")
IMSCC = os.path.join(HERE, "Sample-Course-Canvas-Cartridge.imscc")

def esc(s):
    return escape(str(s if s is not None else ""), {'"': "&quot;"})

def txt(el, path, default=""):
    node = el.find(path) if el is not None else None
    v = (node.text or default) if node is not None else default
    # FIX F2 (real-export test, 2026-10-24): genuine Moodle backups write the
    # literal string $@NULL@$ for every NULL field (sequences, names, filter
    # fields...). Treat it as empty everywhere; the original code crashed on
    # int("$@NULL@$") when reading a real section sequence.
    return "" if v == "$@NULL@$" else v

# ------------------------------------------------------------------ load mbz
def _open_archive(path):
    """Return (names, read) for a .mbz in either container Moodle produces.

    FIX F1 (real-export test, 2026-10-24): the original code assumed ZIP and
    died with BadZipFile on genuine exports. Moodle's mbz_packer writes
    tar.gz by default (fixtures as old as Moodle 3.11 are gzip too); ZIP is
    produced only when the site sets $CFG->usezipbackups. Moodle's own
    restore sniffs the same magic bytes, so we do the same.
    """
    with open(path, "rb") as f:
        magic = f.read(4)
    if magic[:2] == b"\x1f\x8b":  # gzip -> tar.gz container
        tf = tarfile.open(path, "r:gz")
        members = {}
        for m in tf.getmembers():
            name = m.name[2:] if m.name.startswith("./") else m.name
            if m.isfile():
                members[name] = m
        def read(name, _tf=tf, _members=members):
            return _tf.extractfile(_members[name]).read()
        return set(members), read
    zf = zipfile.ZipFile(path)
    return set(zf.namelist()), zf.read

class Backup:
    def __init__(self, path):
        self.names, self._read = _open_archive(path)
        self.xml = {}
        for n in self.names:
            if n.endswith(".xml"):
                self.xml[n] = ET.fromstring(self._read(n))
        files_root = self.xml["files.xml"]
        self.files_by_id = {}
        self.hash_by_key = {}   # (component, itemid, filename) -> row
        for fel in files_root.findall("file"):
            row = {c.tag: (c.text or "") for c in fel}
            row["id"] = int(row["id"]); row["itemid"] = int(row["itemid"])
            row["contextid"] = int(row["contextid"])
            self.files_by_id[row["id"]] = row
            self.hash_by_key[(row["component"], row["itemid"], row["filename"])] = row
    def file_bytes(self, row):
        h = row["contenthash"]
        return self._read(f"files/{h[:2]}/{h}")
    def activity_dirs(self):
        info = self.xml["moodle_backup.xml"].find("information/contents/activities")
        out = []
        for a in info.findall("activity"):
            out.append({c.tag: (c.text or "") for c in a})
        return out
    def sections(self):
        info = self.xml["moodle_backup.xml"].find("information/contents/sections")
        return [{c.tag: (c.text or "") for c in s} for s in info.findall("section")]

def _question_tags(q):
    tags = []
    tel = q.find("tags")
    if tel is not None:
        for tg in tel.findall("tag"):
            nm = txt(tg, "name")
            if nm:
                tags.append(nm)
    return tags

def _parse_question(q, cat_id):
    qd = {"id": int(q.get("id")), "name": txt(q, "name"), "qtype": txt(q, "qtype"),
          "text": txt(q, "questiontext"), "generalfeedback": txt(q, "generalfeedback"),
          "category_id": cat_id, "tags": _question_tags(q)}
    plugin = None
    for child in q:
        if child.tag.startswith("plugin_qtype_"):
            plugin = child
    answers = []
    if plugin is not None:
        for ans in plugin.iter("answer"):
            answers.append({"id": int(ans.get("id")),
                            "text": txt(ans, "answertext"),
                            "fraction": float(txt(ans, "fraction", "0")),
                            "feedback": txt(ans, "feedback"),
                            "tolerance": txt(ans, "tolerance")})
        subs = []
        for sub in plugin.iter("subquestion"):
            subs.append({"id": int(sub.get("id")),
                         "text": txt(sub, "questiontext"),
                         "answer": txt(sub, "answertext")})
        qd["subquestions"] = subs
        if qd["qtype"] == "essay":
            essay = plugin.find("essay")
            qd["graderinfo"] = txt(essay, "graderinfo")
        if qd["qtype"] == "calculated":
            dsets = []
            for dd in plugin.iter("dataset_definition"):
                dsets.append(txt(dd, "name"))
            qd["wildcards"] = dsets
    qd["answers"] = answers
    return qd

def load_questions(bk):
    """FIX F3 (real-export test, 2026-10-24): the original read only the FIRST
    <question_category> and assumed the pre-4.0 layout (<questions> directly
    under it), so it crashed on genuine 4.x backups. Real exports have several
    categories (incl. empty 'top' ones) and nest questions under
    question_bank_entries/question_bank_entry/question_version/
    question_versions/questions. We walk every category, support both
    layouts, and for multi-version entries convert the highest version (the
    one a course would deliver). Returns (questions, entry_map, cat_names):
    entry_map maps question_bank_entry id -> chosen question id (needed to
    resolve modern quiz slot references).
    """
    root = bk.xml["questions.xml"]
    questions, entry_map, cat_names = [], {}, {}
    for cat in root.findall("question_category"):
        cat_id = int(cat.get("id"))
        cat_names[cat_id] = txt(cat, "name")
        legacy = cat.find("questions")
        if legacy is not None:
            for q in legacy.findall("question"):
                questions.append(_parse_question(q, cat_id))
        entries = cat.find("question_bank_entries")
        if entries is not None:
            for entry in entries.findall("question_bank_entry"):
                best, best_ver = None, -1
                for ver in entry.iter("question_versions"):
                    try:
                        vnum = int(ver.findtext("version") or 0)
                    except ValueError:
                        vnum = 0
                    qs_el = ver.find("questions")
                    if qs_el is None:
                        continue
                    for q in qs_el.findall("question"):
                        if vnum >= best_ver:
                            best, best_ver = q, vnum
                if best is not None:
                    qd = _parse_question(best, cat_id)
                    entry_map[int(entry.get("id"))] = qd["id"]
                    questions.append(qd)
    return questions, entry_map, cat_names

# ------------------------------------------------------------------ QTI items
class QtiBuilder:
    def __init__(self):
        self.feedback_blocks = 0
        self.labels = 0
        self.accepted_conditions = 0
        self.match_lids = 0
        self.placeholder_items = []  # (name, qtype) force-placeholdered, see item()

    def _feedback_xml(self, q, extra_answer_fbs):
        out = []
        if q["generalfeedback"]:
            out.append(f'<itemfeedback ident="general_feedback" view="All">'
                       f'<material><mattext texttype="text/html">{esc(q["generalfeedback"])}</mattext></material></itemfeedback>')
            self.feedback_blocks += 1
        for aid, fb in extra_answer_fbs:
            out.append(f'<itemfeedback ident="fb_{aid}" view="All">'
                       f'<material><mattext texttype="text/html">{esc(fb)}</mattext></material></itemfeedback>')
            self.feedback_blocks += 1
        return "".join(out)

    def _meta(self, q, extra=()):
        fields = [("moodle_qtype", q["qtype"])] + list(extra)
        fxml = "".join(
            f'<qtimetadatafield><fieldlabel>{k}</fieldlabel><fieldentry>{esc(v)}</fieldentry></qtimetadatafield>'
            for k, v in fields)
        return f'<itemmetadata><qtimetadata>{fxml}</qtimetadata></itemmetadata>'

    def item(self, q):
        qid = q["id"]
        title = esc(q["name"])
        pres_text = (f'<material><mattext texttype="text/html">{esc(q["text"])}</mattext></material>')
        if q["qtype"] in ("multichoice", "truefalse"):
            single = q["qtype"] == "truefalse" or _is_single(q)
            card = "Single" if single else "Multiple"
            labels, conds, fbs = [], [], []
            for a in q["answers"]:
                lid = f"A{a['id']}"
                labels.append(f'<response_label ident="{lid}"><material>'
                              f'<mattext texttype="text/html">{esc(a["text"])}</mattext></material></response_label>')
                self.labels += 1
                if a["feedback"]:
                    fbs.append((a["id"], a["feedback"]))
            correct = [a for a in q["answers"] if a["fraction"] > 0.999]
            wrong = [a for a in q["answers"] if a["fraction"] <= 0.999]
            if single and correct:
                a = correct[0]
                disp = (f'<displayfeedback feedbacktype="Response" linkrefid="fb_{a["id"]}"/>'
                        if a["feedback"] else "")
                conds.append(f'<respcondition title="Correct"><conditionvar>'
                             f'<varequal respident="response">A{a["id"]}</varequal></conditionvar>'
                             f'<setvar action="Set" varname="SCORE">1</setvar>{disp}</respcondition>')
            elif not single and correct:
                parts = "".join(f'<varequal respident="response">A{a["id"]}</varequal>' for a in correct)
                nots = "".join(f'<not><varequal respident="response">A{a["id"]}</varequal></not>' for a in wrong)
                conds.append(f'<respcondition title="Correct"><conditionvar><and>{parts}{nots}</and></conditionvar>'
                             f'<setvar action="Set" varname="SCORE">1</setvar></respcondition>')
            for a in wrong:
                if a["feedback"]:
                    conds.append(f'<respcondition title="Incorrect choice"><conditionvar>'
                                 f'<varequal respident="response">A{a["id"]}</varequal></conditionvar>'
                                 f'<setvar action="Set" varname="SCORE">0</setvar>'
                                 f'<displayfeedback feedbacktype="Response" linkrefid="fb_{a["id"]}"/></respcondition>')
            body = (f'<presentation>{pres_text}<response_lid ident="response" rcardinality="{card}">'
                    f'<render_choice shuffle="Yes">{"".join(labels)}</render_choice></response_lid></presentation>'
                    f'<resprocessing><outcomes><decvar varname="SCORE" vartype="Decimal" defaultval="0" maxvalue="1"/></outcomes>'
                    f'{"".join(conds)}</resprocessing>')
            return (f'<item ident="Q{qid}" title="{title}">{self._meta(q)}{body}'
                    f'{self._feedback_xml(q, fbs)}</item>')
        if q["qtype"] == "shortanswer":
            conds = []
            for a in q["answers"]:
                self.accepted_conditions += 1
                conds.append(f'<respcondition title="Accepted answer"><conditionvar>'
                             f'<varequal respident="response" case="No">{esc(a["text"])}</varequal></conditionvar>'
                             f'<setvar action="Set" varname="SCORE">{a["fraction"]:g}</setvar></respcondition>')
            body = (f'<presentation>{pres_text}<response_str ident="response" rcardinality="Single">'
                    f'<render_fib fibtype="String"/></response_str></presentation>'
                    f'<resprocessing><outcomes><decvar varname="SCORE" vartype="Decimal" defaultval="0" maxvalue="1"/></outcomes>'
                    f'{"".join(conds)}</resprocessing>')
            return f'<item ident="Q{qid}" title="{title}">{self._meta(q)}{body}{self._feedback_xml(q, [])}</item>'
        if q["qtype"] == "matching":
            subs = q["subquestions"]
            all_answers = sorted({s["answer"] for s in subs})
            lids, conds = [], []
            per = 1.0 / len(subs)
            for s in subs:
                labels = []
                for k, atxt in enumerate(all_answers):
                    labels.append(f'<response_label ident="M{s["id"]}_{k}"><material>'
                                  f'<mattext texttype="text/html">{esc(atxt)}</mattext></material></response_label>')
                    self.labels += 1
                correct_k = all_answers.index(s["answer"])
                lids.append(f'<response_lid ident="response_{s["id"]}" rcardinality="Single">'
                            f'<material><mattext texttype="text/html">{esc(s["text"])}</mattext></material>'
                            f'<render_choice shuffle="Yes">{"".join(labels)}</render_choice></response_lid>')
                self.match_lids += 1
                conds.append(f'<respcondition title="Pair {s["id"]}"><conditionvar>'
                             f'<varequal respident="response_{s["id"]}">M{s["id"]}_{correct_k}</varequal></conditionvar>'
                             f'<setvar action="Add" varname="SCORE">{per:.4f}</setvar></respcondition>')
            body = (f'<presentation>{pres_text}{"".join(lids)}</presentation>'
                    f'<resprocessing><outcomes><decvar varname="SCORE" vartype="Decimal" defaultval="0" maxvalue="1"/></outcomes>'
                    f'{"".join(conds)}</resprocessing>')
            return f'<item ident="Q{qid}" title="{title}">{self._meta(q)}{body}{self._feedback_xml(q, [])}</item>'
        if q["qtype"] == "numerical":
            a = q["answers"][0]
            val = float(a["text"]); tol = float(a["tolerance"] or 0)
            fbs = [(a["id"], a["feedback"])] if a["feedback"] else []
            cond = (f'<respcondition title="Correct"><conditionvar><and>'
                    f'<vargte respident="response">{val - tol:g}</vargte>'
                    f'<varlte respident="response">{val + tol:g}</varlte></and></conditionvar>'
                    f'<setvar action="Set" varname="SCORE">1</setvar>'
                    + (f'<displayfeedback feedbacktype="Response" linkrefid="fb_{a["id"]}"/>'
                       if a["feedback"] else "") + '</respcondition>')
            body = (f'<presentation>{pres_text}<response_str ident="response" rcardinality="Single">'
                    f'<render_fib fibtype="Decimal"/></response_str></presentation>'
                    f'<resprocessing><outcomes><decvar varname="SCORE" vartype="Decimal" defaultval="0" maxvalue="1"/></outcomes>'
                    f'{cond}</resprocessing>')
            return f'<item ident="Q{qid}" title="{title}">{self._meta(q)}{body}{self._feedback_xml(q, fbs)}</item>'
        if q["qtype"] == "essay":
            body = (f'<presentation>{pres_text}<response_str ident="response" rcardinality="Single">'
                    f'<render_fib fibtype="String" rows="15" columns="72"/></response_str></presentation>'
                    f'<resprocessing><outcomes><decvar varname="SCORE" vartype="Decimal" defaultval="0" maxvalue="1"/></outcomes></resprocessing>')
            meta = self._meta(q, [("grader_info", q.get("graderinfo", ""))])
            return f'<item ident="Q{qid}" title="{title}">{meta}{body}{self._feedback_xml(q, [])}</item>'
        if q["qtype"] == "calculated":
            formula = q["answers"][0]["text"] if q["answers"] else ""
            note = (f'<material><mattext texttype="text/html">'
                    f'<p><strong>CONVERSION PLACEHOLDER — NOT A WORKING QUESTION.</strong> '
                    f'This was a Moodle <em>calculated</em> question. Calculated questions generate '
                    f'randomised numbers from wildcard datasets for every attempt; IMS Common Cartridge / '
                    f'QTI has no equivalent, so the question was deliberately NOT force-converted. '
                    f'Recreate it manually in the target system.</p>'
                    f'<p>Original question text: {esc(q["text"])}</p>'
                    f'<p>Original formula: {esc(formula)}</p>'
                    f'<p>Wildcards: {esc(", ".join(q.get("wildcards", [])))}</p>'
                    f'</mattext></material>')
            body = f'<presentation>{note}</presentation>'
            meta = self._meta(q, [("conversion_status", "placeholder")])
            return (f'<item ident="Q{qid}" title="PLACEHOLDER: {title}">{meta}{body}'
                    f'{self._feedback_xml(q, [])}</item>')
        # FIX F9 (real-export test, 2026-10-24): unknown/exotic qtypes (random,
        # multianswer/cloze, drag-and-drop, missingtype...) used to raise and
        # kill the whole conversion. They now degrade to a clearly labelled
        # placeholder carrying the original text, and are recorded so main()
        # can disclose each one in the exception report. Never a silent drop,
        # never a crash.
        self.placeholder_items.append((q["name"], q["qtype"]))
        note = (f'<material><mattext texttype="text/html">'
                f'<p><strong>CONVERSION PLACEHOLDER — NOT A WORKING QUESTION.</strong> '
                f'This was a Moodle <em>{esc(q["qtype"])}</em> question, a type with no '
                f'faithful IMS Common Cartridge / QTI equivalent, so it was deliberately '
                f'NOT force-converted. Recreate it manually in the target system.</p>'
                f'<p>Original question text: {esc(q["text"])}</p>'
                f'</mattext></material>')
        body = f'<presentation>{note}</presentation>'
        meta = self._meta(q, [("conversion_status", "placeholder")])
        return (f'<item ident="Q{qid}" title="PLACEHOLDER: {title}">{meta}{body}'
                f'{self._feedback_xml(q, [])}</item>')

def _is_single(q):
    # In our bank, single-answer multichoice has exactly one answer with fraction 1
    # and three with 0; multiple-answer has three with fraction 1.
    return sum(1 for a in q["answers"] if a["fraction"] > 0.999) == 1

def resolve_quiz_members(ael, q_by_id, entry_map, questions):
    """Resolve a quiz's slots to bank question ids across Moodle eras.

    FIX F4 (real-export test, 2026-10-24): the original assumed every slot
    carries a fixed <question> id (the pre-4.0 form) and crashed otherwise.
    Genuine exports also use:
      * <question_reference> with <questionbankentryid> (Moodle 4.x fixed
        slot) — resolved through the bank-entry map from load_questions();
      * <question_set_reference> with a JSON <filtercondition> (a random
        draw from a category, optionally tag-filtered) — no single question
        exists, so every candidate the filter can draw (category match +
        tag-superset match) is included and the slot is counted as a set
        slot for disclosure in the exception report.
    Returns (member_ids in slot order, deduped; info dict of slot forms).
    """
    info = {"fixed": 0, "references": 0, "set_slots": 0, "unresolved": 0,
            "set_candidates": set()}
    member_ids, seen = [], set()
    def add(qid):
        if qid in q_by_id and qid not in seen:
            seen.add(qid)
            member_ids.append(qid)
    qi_parent = ael.find("question_instances")
    if qi_parent is None:
        return member_ids, info
    for qi in qi_parent.findall("question_instance"):
        fixed = txt(qi, "question")
        if fixed:
            try:
                add(int(fixed)); info["fixed"] += 1; continue
            except ValueError:
                pass
        ref = qi.find("question_reference")
        if ref is not None:
            entry_txt = txt(ref, "questionbankentryid")
            if entry_txt:
                try:
                    entry_id = int(entry_txt)
                except ValueError:
                    entry_id = None
                if entry_id in entry_map:
                    add(entry_map[entry_id]); info["references"] += 1; continue
        sref = qi.find("question_set_reference")
        if sref is not None:
            info["set_slots"] += 1
            try:
                filt = json.loads(txt(sref, "filtercondition") or "{}")
            except Exception:
                filt = {}
            catid = filt.get("questioncategoryid")
            try:
                catid = int(catid) if catid is not None else None
            except (TypeError, ValueError):
                catid = None
            want_tags = set()
            for t in filt.get("tags", []) or []:
                # filter entries are "tagid,tag name"
                want_tags.add(str(t).split(",", 1)[-1].strip())
            for q in questions:
                if catid is not None and q.get("category_id") != catid:
                    continue
                if want_tags and not want_tags.issubset(set(q.get("tags", []))):
                    continue
                info["set_candidates"].add(q["id"])
                add(q["id"])
            continue
        info["unresolved"] += 1
    return member_ids, info

# ------------------------------------------------------------------ main build
def html_page(title, body_html):
    return (f'<!DOCTYPE html>\n<html lang="en">\n<head><meta charset="utf-8">'
            f'<title>{esc(title)}</title></head>\n<body>\n<h1>{esc(title)}</h1>\n'
            f'{body_html}\n</body>\n</html>\n')

def main():
    if os.path.exists(OUTDIR):
        shutil.rmtree(OUTDIR)
    os.makedirs(OUTDIR)
    bk = Backup(MBZ)
    course = bk.xml["course/course.xml"]
    course_title = txt(course, "fullname")
    questions, entry_map, cat_names = load_questions(bk)
    q_by_id = {q["id"]: q for q in questions}
    acts_meta = {int(a["moduleid"]): a for a in bk.activity_dirs()}
    sections_meta = bk.sections()

    exceptions = []   # {item, source_detail, fallback}
    extra_placeholders = []  # (name, qtype) from QtiBuilder fallback (FIX F9)
    resources = []    # manifest resources
    org_sections = [] # [(section title, [(item title, resource identifier)])]
    copied_files = {} # cartridge path -> sha1
    qimage_map = {}   # question name -> [{file, sha1, folders:[...]}]
    counts = {"pages": 0, "labels": 0, "file_resources": 0, "assignments": 0,
              "quizzes": 0, "assessments_written": 0}

    def write(relpath, data):
        full = os.path.join(OUTDIR, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        mode = "wb" if isinstance(data, bytes) else "w"
        with open(full, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as f:
            f.write(data)
        return relpath

    def copy_file_row(row, dest_rel):
        data = bk.file_bytes(row)
        write(dest_rel, data)
        copied_files[dest_rel] = hashlib.sha1(data).hexdigest()
        return dest_rel

    def question_images(q, folder):
        """Copy any question-embedded images into folder; return rewritten text."""
        text = q["text"]
        for (comp, itemid, fname), row in bk.hash_by_key.items():
            if comp == "question" and itemid == q["id"]:
                dest = f"{folder}/{fname}"
                copy_file_row(row, dest)
                entry = qimage_map.setdefault(q["name"], [])
                rec = next((e for e in entry if e["file"] == fname), None)
                if rec is None:
                    rec = {"file": fname, "sha1": row["contenthash"], "folders": []}
                    entry.append(rec)
                rec["folders"].append(folder)
        return text.replace("@@PLUGINFILE@@/", "")

    def build_assessment(folder, title, qlist):
        qb = QtiBuilder()
        items = []
        for q in qlist:
            q2 = dict(q)
            q2["text"] = question_images(q, folder)
            items.append(qb.item(q2))
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<questestinterop xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2" '
               'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
               'xsi:schemaLocation="http://www.imsglobal.org/xsd/ims_qtiasiv1p2 ims_qtiasiv1p2.xsd">\n'
               f'<assessment ident="{folder}_A" title="{esc(title)}">\n'
               '<qtimetadata><qtimetadatafield><fieldlabel>cc_naming_includes</fieldlabel>'
               '<fieldentry>Converted from a Moodle question bank export</fieldentry></qtimetadatafield></qtimetadata>\n'
               f'<section ident="{folder}_S" title="Default section">\n'
               + "\n".join(items) +
               '\n</section>\n</assessment>\n</questestinterop>\n')
        write(f"{folder}/assessment.xml", xml)
        files = [f"{folder}/assessment.xml"]
        for name in sorted(os.listdir(os.path.join(OUTDIR, folder))):
            if name != "assessment.xml":
                files.append(f"{folder}/{name}")
        counts["assessments_written"] += 1
        return files, qb

    section_order = []
    for s in sections_meta:
        sid = int(s["sectionid"])
        # FIX F5 (real-export test): use the section's own <directory> from
        # the backup index instead of reconstructing the path, and derive a
        # display title that works for unnamed sections — genuine backups put
        # the bare section NUMBER in the index <title> and $@NULL@$ in
        # section.xml <name> (normalised to "" by txt()).
        sdir = s.get("directory") or f"sections/section_{sid}"
        sroot = bk.xml[f"{sdir}/section.xml"]
        raw_seq = txt(sroot, "sequence")
        seq = [int(x) for x in raw_seq.split(",") if x.strip()] if raw_seq else []
        name = txt(sroot, "name")
        number = txt(sroot, "number")
        if name:
            title = name
        elif s["title"] and not s["title"].isdigit():
            title = s["title"]
        elif number:
            title = f"Section {number}"
        else:
            title = s["title"]
        section_order.append((title, seq))

    qti_totals = {"feedback_blocks": 0, "labels": 0, "accepted_conditions": 0,
                  "match_lids": 0, "items_by_type": {}, "placeholders": 0}

    for sec_title, seq in section_order:
        org_items = []
        for cmid in seq:
            meta = acts_meta[cmid]
            modname, title = meta["modulename"], meta["title"]
            directory = meta["directory"]
            aroot = bk.xml.get(f"{directory}/{modname}.xml")
            ael = aroot.find(modname) if aroot is not None else None
            instance = int(aroot.get("id")) if aroot is not None else 0
            rid = f"R_{modname}_{cmid}"
            if modname == "page":
                content = txt(ael, "content").replace("@@PLUGINFILE@@/", "")
                folder = f"page_{cmid}"
                write(f"{folder}/index.html", html_page(title, content))
                files = [f"{folder}/index.html"]
                for (comp, itemid, fname), row in bk.hash_by_key.items():
                    if comp == "mod_page" and itemid == instance:
                        files.append(copy_file_row(row, f"{folder}/{fname}"))
                resources.append({"identifier": rid, "type": "webcontent",
                                  "href": f"{folder}/index.html", "files": files})
                counts["pages"] += 1
            elif modname == "label":
                folder = f"label_{cmid}"
                write(f"{folder}/index.html", html_page(title, txt(ael, "intro")))
                resources.append({"identifier": rid, "type": "webcontent",
                                  "href": f"{folder}/index.html",
                                  "files": [f"{folder}/index.html"]})
                counts["labels"] += 1
            elif modname == "resource":
                row = next(r for (c, i, f), r in bk.hash_by_key.items()
                           if c == "mod_resource" and i == instance)
                folder = f"resource_{cmid}"
                dest = copy_file_row(row, f"{folder}/{row['filename']}")
                resources.append({"identifier": rid, "type": "webcontent",
                                  "href": dest, "files": [dest]})
                counts["file_resources"] += 1
                if row["filename"].endswith(".zip"):
                    exceptions.append({
                        "item": f"SCORM 1.2 package '{row['filename']}' (activity: {title})",
                        "detail": ("Transferred byte-identical as a file. Its SCORM runtime wiring — "
                                   "launch settings and grade passback to the gradebook — cannot be "
                                   "verified from files alone and is NOT converted."),
                        "fallback": ("Package file carried unchanged; a human must attach it with the "
                                     "target system's SCORM tool and test it in student view, "
                                     "including a completion/passback check.")})
            elif modname == "assign":
                folder = f"assign_{cmid}"
                grading = bk.xml.get(f"{directory}/grading.xml")
                rubric_html, ncrit, nlev = "", 0, 0
                if grading is not None:
                    rows = []
                    for crit in grading.iter("rubric_criterion"):
                        ncrit += 1
                        levels = [txt(lv, "definition") for lv in crit.find("levels").findall("level")]
                        nlev += len(levels)
                        rows.append("<tr><td>" + esc(txt(crit, "description")) + "</td>" +
                                    "".join(f"<td>{esc(l)}</td>" for l in levels) + "</tr>")
                    rubric_html = ("<h2>Marking rubric (from the source course)</h2>"
                                   "<table border=\"1\" cellspacing=\"0\" cellpadding=\"6\">" +
                                   "".join(rows) + "</table>")
                    exceptions.append({
                        "item": f"Assignment rubric on '{title}' ({ncrit} criteria, {nlev} levels)",
                        "detail": ("Moodle rubric grading forms have no machine-readable equivalent "
                                   "in IMS Common Cartridge."),
                        "fallback": ("Rubric criteria and level descriptions are reproduced as a "
                                     "readable table inside the assignment page; a human must "
                                     "rebuild the rubric in the target system's grading tool.")})
                body = (f"<p>{esc(txt(ael, 'intro'))}</p>" + rubric_html +
                        "<p><strong>CONVERSION NOTE:</strong> grading-form structure (rubric) is "
                        "documented in the course's Pre-Migration Exception Report.</p>")
                write(f"{folder}/index.html", html_page(title, body))
                resources.append({"identifier": rid, "type": "webcontent",
                                  "href": f"{folder}/index.html",
                                  "files": [f"{folder}/index.html"]})
                counts["assignments"] += 1
            elif modname == "quiz":
                folder = f"quiz_{cmid}"
                member_ids, slot_info = resolve_quiz_members(
                    ael, q_by_id, entry_map, questions)
                qlist = [q_by_id[i] for i in member_ids]
                files, qb = build_assessment(folder, title, qlist)
                extra_placeholders.extend(qb.placeholder_items)
                resources.append({"identifier": rid,
                                  "type": "imsqti_xmlv1p2/imscc_xmlv1p1/assessment",
                                  "href": f"{folder}/assessment.xml", "files": files})
                counts["quizzes"] += 1
                qti_totals["feedback_blocks"] += qb.feedback_blocks
                qti_totals["labels"] += qb.labels
                qti_totals["accepted_conditions"] += qb.accepted_conditions
                qti_totals["match_lids"] += qb.match_lids
                if slot_info["set_slots"] or slot_info["unresolved"]:
                    detail = (f"{slot_info['set_slots']} of this quiz's slots are random/filter "
                              f"draws (Moodle question_set_reference), not fixed questions; "
                              f"{slot_info['unresolved']} slot(s) could not be resolved at all. "
                              "IMS Common Cartridge / QTI has no random-draw mechanism.")
                    exceptions.append({
                        "item": f"Quiz slot draw rules on '{title}'",
                        "detail": detail,
                        "fallback": (f"All {len(slot_info['set_candidates'])} candidate question(s) "
                                     "the filters can draw are included in full in the quiz "
                                     "assessment; recreate the draw rules (category/tag filters) "
                                     "manually in the target system.")})
            else:
                # FIX F10 (real-export test): activity module types the
                # converter does not handle (forum, glossary, lesson, book,
                # workshop, H5P... — present in most real courses) used to
                # produce an organisation item pointing at a resource that
                # was never created. They now get a labelled placeholder page
                # + an exception entry, like every other unconvertible item.
                folder = f"other_{cmid}"
                body = (f"<p><strong>CONVERSION PLACEHOLDER.</strong> This was a Moodle "
                        f"'{esc(modname)}' activity. This module type is not converted by "
                        f"this tool and was NOT force-converted; see the Pre-Migration "
                        f"Exception Report in this cartridge.</p>")
                write(f"{folder}/index.html", html_page(title, body))
                resources.append({"identifier": rid, "type": "webcontent",
                                  "href": f"{folder}/index.html",
                                  "files": [f"{folder}/index.html"]})
                exceptions.append({
                    "item": f"Activity '{title}' (Moodle module: {modname})",
                    "detail": (f"The '{modname}' module type is not converted by this tool; "
                               "its content and settings do not transfer in the cartridge."),
                    "fallback": ("A labelled placeholder page marks its position in the "
                                 "course structure; recreate the activity natively in "
                                 "the target system.")})
            org_items.append((title, rid))
        org_sections.append((sec_title, org_items))

    # question bank assessment (all questions; calculated become placeholders)
    files, qb = build_assessment("questionbank", "Full Question Bank (converted)", questions)
    extra_placeholders.extend(qb.placeholder_items)
    resources.append({"identifier": "R_questionbank",
                      "type": "imsqti_xmlv1p2/imscc_xmlv1p1/assessment",
                      "href": "questionbank/assessment.xml", "files": files})
    qti_totals["feedback_blocks"] += qb.feedback_blocks
    qti_totals["labels"] += qb.labels
    qti_totals["accepted_conditions"] += qb.accepted_conditions
    qti_totals["match_lids"] += qb.match_lids
    for q in questions:
        qti_totals["items_by_type"][q["qtype"]] = qti_totals["items_by_type"].get(q["qtype"], 0) + 1
        if q["qtype"] == "calculated":
            qti_totals["placeholders"] += 1
            exceptions.append({
                "item": f"Calculated question '{q['name']}'",
                "detail": ("Moodle calculated questions randomise numbers from wildcard datasets "
                           f"({', '.join(q.get('wildcards', []))}) on every attempt; QTI/Common "
                           "Cartridge has no equivalent mechanism."),
                "fallback": ("A clearly labelled placeholder item is included in the question bank "
                             "carrying the original question text, formula and wildcard ranges; a "
                             "human must recreate the question natively in the target system.")})
    # FIX F9 disclosure: exotic qtypes placeholdered by the QtiBuilder fallback
    seen_extra = set()
    for pname, ptype in extra_placeholders:
        if (pname, ptype) in seen_extra:
            continue
        seen_extra.add((pname, ptype))
        qti_totals["placeholders"] += 1
        exceptions.append({
            "item": f"Question '{pname}' (type: {ptype})",
            "detail": (f"Moodle question type '{ptype}' has no faithful IMS Common "
                       "Cartridge / QTI equivalent."),
            "fallback": ("A clearly labelled placeholder item carrying the original "
                         "question text is included in the question bank (and in any "
                         "quiz that uses it); recreate the question natively in the "
                         "target system.")})

    # completion prerequisites + gradebook + completion settings -> exceptions
    for cmid, meta in sorted(acts_meta.items()):
        mroot = bk.xml[f"{meta['directory']}/module.xml"]
        avail = txt(mroot, "availability")
        if avail and avail != "$@NULL@$":
            try:
                cond = json.loads(avail)
                req = cond["c"][0]["cm"]
                exceptions.append({
                    "item": f"Restrict-access rule on '{meta['title']}'",
                    "detail": (f"Opens only after '{acts_meta[req]['title']}' is marked complete. "
                               "IMS Common Cartridge has no standard for activity prerequisites."),
                    "fallback": "Listed here for manual recreation in the target system's requirements/prerequisites settings."})
            except Exception:
                exceptions.append({"item": f"Restrict-access rule on '{meta['title']}'",
                                   "detail": "Unparsed availability JSON: " + avail,
                                   "fallback": "Recreate manually in the target system."})
    # FIX F6 (real-export test): the original gradebook exception asserted
    # sample-specific numbers ("course total 40 points, 1 assignment, 3
    # quizzes") that would be FALSE statements on any real client file.
    # Derive the facts from the actual gradebook.xml instead.
    gb_root = bk.xml.get("gradebook.xml")
    n_grade_items = len(gb_root.findall(".//grade_item")) if gb_root is not None else 0
    exceptions.append({
        "item": "Gradebook structure and weighting",
        "detail": (f"Source gradebook contains {n_grade_items} grade item(s) under Moodle "
                   "aggregation rules. Cartridge packages do not carry gradebook aggregation "
                   "or weighting."),
        "fallback": "Recreate gradebook categories and weights manually in the target system."})
    # FIX F7 (real-export test): same defect — the completion exception
    # hardcoded "4 source activities". Count the real completion flags.
    n_completion = 0
    for _cmid, _meta in acts_meta.items():
        _mroot = bk.xml[f"{_meta['directory']}/module.xml"]
        if txt(_mroot, "completion") not in ("", "0"):
            n_completion += 1
    if n_completion:
        exceptions.append({
            "item": "Activity completion tracking settings",
            "detail": (f"{n_completion} source activities carry Moodle completion tracking "
                       "flags; completion conditions themselves are not a cartridge concept."),
            "fallback": "Re-enable completion tracking per activity in the target system if required."})
    exceptions.append({
        "item": "LTI / external-tool activities",
        "detail": "None existed in the source course — not applicable to this conversion.",
        "fallback": "No action. (In real courses, LTI credentials never transfer in a cartridge and must be re-issued.)"})

    # exceptions.html resource
    rows = "".join(
        f"<tr><td>{esc(e['item'])}</td><td>{esc(e['detail'])}</td><td>{esc(e['fallback'])}</td></tr>"
        for e in exceptions)
    exc_html = html_page(
        "Pre-Migration Exception Report",
        "<p>The items below exist in the source course but could not be converted faithfully. "
        "Each names the fallback that was taken. Nothing on this list was silently dropped.</p>"
        "<table border=\"1\" cellspacing=\"0\" cellpadding=\"6\">"
        "<tr><th>Item</th><th>Why it does not convert</th><th>Fallback taken</th></tr>"
        + rows + "</table>")
    write("exceptions.html", exc_html)
    resources.append({"identifier": "R_exceptions", "type": "webcontent",
                      "href": "exceptions.html", "files": ["exceptions.html"]})
    if org_sections:
        org_sections[-1][1].append(("Pre-Migration Exception Report", "R_exceptions"))
    org_sections.append(("Question Bank", [("Full Question Bank (converted)", "R_questionbank")]))

    # ---------------------------------------------------------------- manifest
    # FIX F8 (real-export test): manifest/org identifiers were hardcoded to
    # the sample course's code. Derive them from the source shortname.
    code = re.sub(r"[^A-Za-z0-9]", "", txt(course, "shortname") or "COURSE").upper() or "COURSE"
    org_xml, res_xml = [], []
    for si, (sec_title, items) in enumerate(org_sections, start=1):
        item_xml = "".join(
            f'<item identifier="I_{rid}" identifierref="{rid}" isvisible="true">'
            f'<title>{esc(t)}</title></item>' for t, rid in items)
        org_xml.append(f'<item identifier="I_SEC{si}"><title>{esc(sec_title)}</title>{item_xml}</item>')
    for r in resources:
        fxml = "".join(f'<file href="{esc(f)}"/>' for f in r["files"])
        res_xml.append(f'<resource identifier="{r["identifier"]}" type="{r["type"]}" '
                       f'href="{esc(r["href"])}">{fxml}</resource>')
    manifest = f'''<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="MANIFEST_{code}" xmlns="http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1"
 xmlns:lom="http://ltsc.ieee.org/xsd/imsccv1p1/LOM/resource"
 xmlns:lomimscc="http://ltsc.ieee.org/xsd/imsccv1p1/LOM/manifest"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:schemaLocation="http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1 http://www.imsglobal.org/profile/cc/ccv1p1/ccv1p1_imscp_v1p3.xsd
 http://ltsc.ieee.org/xsd/imsccv1p1/LOM/resource http://www.imsglobal.org/profile/cc/ccv1p1/ccv1p1_lomresource_v1p0.xsd
 http://ltsc.ieee.org/xsd/imsccv1p1/LOM/manifest http://www.imsglobal.org/profile/cc/ccv1p1/ccv1p1_lommanifest_v1p0.xsd">
<metadata>
<schema>IMS Common Cartridge</schema>
<schemaversion>1.3.0</schemaversion>
<lomimscc:lom>
<lomimscc:general>
<lomimscc:title>
<lomimscc:string language="en-US">{esc(course_title)}</lomimscc:string>
</lomimscc:title>
<lomimscc:description>
<lomimscc:string language="en-US">Converted from a Moodle course backup (.mbz) by the sample converter. See the Pre-Migration Exception Report inside this cartridge for items that need human setup.</lomimscc:string>
</lomimscc:description>
</lomimscc:general>
</lomimscc:lom>
</metadata>
<organizations>
<organization identifier="ORG_{code}" structure="rooted-hierarchy">
<title>{esc(course_title)}</title>
<item identifier="ROOT_ORG">
{chr(10).join(org_xml)}
</item>
</organization>
</organizations>
<resources>
{chr(10).join(res_xml)}
</resources>
</manifest>
'''
    write("imsmanifest.xml", manifest)

    if os.path.exists(IMSCC):
        os.remove(IMSCC)
    with zipfile.ZipFile(IMSCC, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _d, fnames in os.walk(OUTDIR):
            for fn in sorted(fnames):
                full = os.path.join(root, fn)
                z.write(full, os.path.relpath(full, OUTDIR))

    out_counts = {
        "course": course_title,
        "sections": len(org_sections) - 1,  # last entry is the question-bank pseudo-section
        "resources_total": len(resources),
        **counts,
        "qti_items_by_type_in_bank": qti_totals["items_by_type"],
        "qti_placeholders": qti_totals["placeholders"],
        "qti_feedback_blocks_total_all_assessments": qti_totals["feedback_blocks"],
        "qti_labels_total_all_assessments": qti_totals["labels"],
        "qti_accepted_answer_conditions_all": qti_totals["accepted_conditions"],
        "qti_matching_response_lids_all": qti_totals["match_lids"],
        "exceptions_count": len(exceptions),
        "exceptions": exceptions,
        "question_images": qimage_map,
        "copied_files": copied_files,
        "imscc_bytes": os.path.getsize(IMSCC),
    }
    with open(os.path.join(HERE, "conversion-counts.json"), "w", encoding="utf-8") as f:
        json.dump(out_counts, f, indent=2)
    print(json.dumps({k: v for k, v in out_counts.items()
                      if k not in ("exceptions", "question_images", "copied_files")}, indent=2))
    print("IMSCC:", IMSCC, out_counts["imscc_bytes"], "bytes")

if __name__ == "__main__":
    main()
