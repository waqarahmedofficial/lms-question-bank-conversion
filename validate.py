# -*- coding: utf-8 -*-
"""
validate.py — independent validation of the .mbz and the converted .imscc.

Checks (all must pass):
 A. Every XML file in both archives is well-formed.
 B. The cartridge manifest's every <file href> and resource href resolves to a
    file actually present in the cartridge.
 C. Source backup self-consistency: files.xml contenthashes match the physical
    hashed storage inside the .mbz.
 D. Count reconciliation source -> question bank: questions by type, total
    questions, answer-level + question-level feedback, response options.
 E. Quiz membership reconciliation: each quiz assessment contains exactly the
    question ids its source quiz referenced.
 F. Byte integrity: every unique source file (by SHA-1) is present byte-identical
    somewhere in the cartridge.
 G. PER-QUESTION image integrity (inside the question bank and inside each quiz
    that reuses the question): image bytes in the cartridge match the source
    contenthash for that question's image.
Writes VALIDATION-OUTPUT.txt and exits non-zero on any failure.
"""
import os, sys, json, hashlib, zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
MBZ = os.path.join(HERE, "Sample-Course-Moodle-Backup.mbz")
IMSCC = os.path.join(HERE, "Sample-Course-Canvas-Cartridge.imscc")
NS = {"m": "http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1",
      "q": "http://www.imsglobal.org/xsd/ims_qtiasiv1p2"}
lines, failures = [], []

def check(ok, label, detail=""):
    lines.append(("PASS" if ok else "FAIL") + "  " + label + ((" — " + detail) if detail else ""))
    if not ok:
        failures.append(label)

def t(el, path, default=""):
    n = el.find(path) if el is not None else None
    return (n.text or default) if n is not None else default

# ---------------------------------------------------------------- load
mbz = zipfile.ZipFile(MBZ)
ims = zipfile.ZipFile(IMSCC)
mbz_names = set(mbz.namelist())
ims_names = set(ims.namelist())

# A. XML well-formedness
for label, zf, names in (("mbz", mbz, mbz_names), ("imscc", ims, ims_names)):
    xmls = [n for n in names if n.endswith(".xml")]
    bad = []
    for n in xmls:
        try:
            ET.fromstring(zf.read(n))
        except Exception as e:
            bad.append(f"{n}: {e}")
    check(not bad, f"A/{label}: all {len(xmls)} XML files well-formed", "; ".join(bad))
# nested SCORM manifest inside the cartridge's resource zip
scorm_name = next(n for n in ims_names if n.endswith("scorm-missed-deadline.zip"))
inner = zipfile.ZipFile(__import__("io").BytesIO(ims.read(scorm_name)))
try:
    ET.fromstring(inner.read("imsmanifest.xml"))
    check(True, "A/scorm: nested SCORM imsmanifest.xml well-formed")
except Exception as e:
    check(False, "A/scorm: nested SCORM imsmanifest.xml well-formed", str(e))

# B. manifest resolution
man = ET.fromstring(ims.read("imsmanifest.xml"))
missing = []
n_files = 0
for fel in man.iter("{http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1}file"):
    n_files += 1
    if fel.get("href") not in ims_names:
        missing.append(fel.get("href"))
for rel in man.iter("{http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1}resource"):
    if rel.get("href") not in ims_names:
        missing.append(rel.get("href"))
check(not missing, f"B: manifest — all {n_files} <file> hrefs + resource hrefs resolve",
      "missing: " + ", ".join(missing))

# C. mbz self-consistency
files_root = ET.fromstring(mbz.read("files.xml"))
rows = []
for fel in files_root.findall("file"):
    row = {c.tag: (c.text or "") for c in fel}
    rows.append(row)
bad = []
for r in rows:
    p = f"files/{r['contenthash'][:2]}/{r['contenthash']}"
    if p not in mbz_names:
        bad.append(r["filename"] + " (missing)")
    elif hashlib.sha1(mbz.read(p)).hexdigest() != r["contenthash"]:
        bad.append(r["filename"] + " (hash mismatch)")
check(not bad, f"C: .mbz files.xml — {len(rows)} rows, physical storage present, SHA-1 matches",
      "; ".join(bad))
src_hashes = {r["contenthash"] for r in rows}

# D. counts: source
qroot = ET.fromstring(mbz.read("questions.xml"))
qs = qroot.find("question_category/questions").findall("question")
src_by_type, src_answers, src_fb_ans, src_fb_gen = {}, 0, 0, 0
src_q = {}
for q in qs:
    qtype = t(q, "qtype")
    src_by_type[qtype] = src_by_type.get(qtype, 0) + 1
    src_q[int(q.get("id"))] = {"name": t(q, "name"), "qtype": qtype,
                               "text": t(q, "questiontext")}
    if t(q, "generalfeedback"):
        src_fb_gen += 1
    for child in q:
        if child.tag.startswith("plugin_qtype_"):
            for ans in child.iter("answer"):
                src_answers += 1
                if t(ans, "feedback"):
                    src_fb_ans += 1
# D. counts: converted bank
bank = ET.fromstring(ims.read("questionbank/assessment.xml"))
items = bank.findall(".//q:item", NS)
out_by_type, out_fb, out_labels, placeholders = {}, 0, 0, 0
bank_item_ids = set()
for it in items:
    bank_item_ids.add(it.get("ident"))
    flds = {t(f, "q:fieldlabel", "") if False else f.findtext("q:fieldlabel", "", NS):
            f.findtext("q:fieldentry", "", NS)
            for f in it.findall(".//q:qtimetadatafield", NS)}
    qt = flds.get("moodle_qtype", "?")
    out_by_type[qt] = out_by_type.get(qt, 0) + 1
    if flds.get("conversion_status") == "placeholder":
        placeholders += 1
    out_fb += len(it.findall("q:itemfeedback", NS))
    out_labels += len(it.findall(".//q:response_label", NS))
src_labels = 0
for q in qs:
    plugin = next((c for c in q if c.tag.startswith("plugin_qtype_")), None)
    if plugin is None:
        continue
    qtype = t(q, "qtype")
    if qtype in ("multichoice", "truefalse"):
        # each answer becomes one response_label
        src_labels += len(list(plugin.iter("answer")))
    elif qtype == "matching":
        # each subquestion renders every distinct answer text of the question as an option
        subs = list(plugin.iter("subquestion"))
        src_labels += len(subs) * len({t(s, "answertext") for s in subs})
check(src_by_type == out_by_type, "D1: questions by type reconcile",
      f"source {src_by_type} vs bank {out_by_type}")
check(len(qs) == len(items) == 63, "D2: total questions 63 = 63",
      f"source {len(qs)}, bank {len(items)}")
check(src_fb_ans + src_fb_gen == out_fb,
      "D3: feedback blocks reconcile (answer-level + question-level)",
      f"source {src_fb_ans}+{src_fb_gen}={src_fb_ans + src_fb_gen} vs bank {out_fb}")
check(placeholders == src_by_type.get("calculated", 0) == 3,
      "D4: calculated questions are labelled placeholders, not conversions",
      f"placeholders {placeholders}")
check(src_labels == out_labels, "D5: response options (answers + matching choices) reconcile",
      f"source {src_labels} vs bank {out_labels}")

# E. quiz membership
info = ET.fromstring(mbz.read("moodle_backup.xml")).find("information/contents/activities")
quiz_ok, quiz_detail = True, []
for a in info.findall("activity"):
    if (a.findtext("modulename") or "") != "quiz":
        continue
    cmid = a.findtext("moduleid")
    directory = a.findtext("directory")
    qroot2 = ET.fromstring(mbz.read(f"{directory}/quiz.xml"))
    want = {"Q" + qi.findtext("question") for qi in
            qroot2.find("quiz/question_instances").findall("question_instance")}
    got_root = ET.fromstring(ims.read(f"quiz_{cmid}/assessment.xml"))
    got = {it.get("ident") for it in got_root.findall(".//q:item", NS)}
    quiz_detail.append(f"quiz_{cmid}: {len(got)}/{len(want)}")
    if want != got:
        quiz_ok = False
check(quiz_ok, "E: each quiz assessment holds exactly its source question set",
      ", ".join(quiz_detail))

# F. byte integrity of all unique source files
ims_hashes = {}
for n in ims_names:
    ims_hashes.setdefault(hashlib.sha1(ims.read(n)).hexdigest(), []).append(n)
missing = [h for h in src_hashes if h not in ims_hashes]
check(not missing, f"F: all {len(src_hashes)} unique source files present byte-identical in cartridge",
      f"missing {len(missing)}")

# G. per-question image integrity
qimg_rows = [r for r in rows if r["component"] == "question"]
g_lines, g_fail = [], 0
for r in sorted(qimg_rows, key=lambda x: int(x["itemid"])):
    qid = int(r["itemid"])
    qname = src_q[qid]["name"]
    fname, want = r["filename"], r["contenthash"]
    spots = []
    # bank copy
    p = f"questionbank/{fname}"
    if p in ims_names and hashlib.sha1(ims.read(p)).hexdigest() == want:
        spots.append("questionbank:OK")
    else:
        spots.append("questionbank:MISSING/MISMATCH"); g_fail += 1
    # each quiz containing the question
    for a in info.findall("activity"):
        if (a.findtext("modulename") or "") != "quiz":
            continue
        cmid = a.findtext("moduleid")
        directory = a.findtext("directory")
        qroot2 = ET.fromstring(mbz.read(f"{directory}/quiz.xml"))
        ids = {qi.findtext("question") for qi in
               qroot2.find("quiz/question_instances").findall("question_instance")}
        if str(qid) in ids:
            p2 = f"quiz_{cmid}/{fname}"
            if p2 in ims_names and hashlib.sha1(ims.read(p2)).hexdigest() == want:
                spots.append(f"quiz_{cmid}:OK")
            else:
                spots.append(f"quiz_{cmid}:MISSING/MISMATCH"); g_fail += 1
    g_lines.append(f"    Q{qid} '{qname}' image {fname} sha1={want[:12]}... -> " + ", ".join(spots))
check(g_fail == 0, f"G: per-question image integrity for {len(qimg_rows)} question-image references")
lines.extend(g_lines)

summary = f"\n==== {'ALL CHECKS PASSED' if not failures else 'FAILURES: ' + str(failures)} ===="
lines.append(summary)
out = "\n".join(lines) + "\n"
with open(os.path.join(HERE, "VALIDATION-OUTPUT.txt"), "w", encoding="utf-8") as f:
    f.write(out)
print(out)
sys.exit(1 if failures else 0)
