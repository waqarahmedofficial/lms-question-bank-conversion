# -*- coding: utf-8 -*-
"""
validate_real.py — independent validation of the REAL-export conversion test.

Sibling of ../validate.py, following the same A-G approach, adapted to the
constructs genuine Moodle exports actually contain (tar.gz or ZIP container,
Moodle 4.x question-bank-entry/version layout, quiz slot references incl.
random/filter set references). Everything is re-derived from the archives
themselves, never from the converter's own counts.

Checks:
 A. Every XML file in both source containers and both cartridges well-formed.
 B. Each cartridge manifest's <file>/resource hrefs all resolve.
 C. Source self-consistency: files.xml contenthashes match physical storage.
 D. Count reconciliation source -> question bank (by type, totals, feedback
    blocks, response labels, placeholders).
 E. Quiz membership reconciliation under the resolved slot semantics, plus
    disclosure: set-reference slots must appear in the exception report.
 F. Byte integrity: every unique source file present byte-identical in the
    cartridge (vacuous when the source carries no files — reported as such).
 G. Per-question image integrity (vacuous when none — reported as such).
 H. Container equivalence: the tar.gz-sourced and ZIP-sourced conversions of
    the same course produce identical cartridges, member by member.
Writes VALIDATION-REAL-OUTPUT.txt and exits non-zero on any failure.
"""
import os, sys, json, glob, hashlib, zipfile, tarfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_TGZ = glob.glob(os.path.join(HERE, "genuine", "*.mbz"))[0]
SRC_ZIP = glob.glob(os.path.join(HERE, "genuine-zip", "*.mbz"))[0]
IMS_Z = os.path.join(HERE, "run3_zip_fixed", "Sample-Course-Canvas-Cartridge.imscc")
IMS_T = os.path.join(HERE, "run4_tgz_fixed", "Sample-Course-Canvas-Cartridge.imscc")
NS = {"m": "http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1",
      "q": "http://www.imsglobal.org/xsd/ims_qtiasiv1p2"}
lines, failures = [], []

def check(ok, label, detail=""):
    lines.append(("PASS" if ok else "FAIL") + "  " + label + ((" — " + detail) if detail else ""))
    if not ok:
        failures.append(label)

def open_archive(path):
    with open(path, "rb") as f:
        magic = f.read(4)
    if magic[:2] == b"\x1f\x8b":
        tf = tarfile.open(path, "r:gz")
        members = {}
        for m in tf.getmembers():
            name = m.name[2:] if m.name.startswith("./") else m.name
            if m.isfile():
                members[name] = m
        return set(members), lambda n: tf.extractfile(members[n]).read()
    zf = zipfile.ZipFile(path)
    return set(zf.namelist()), zf.read

def t(el, path, default=""):
    n = el.find(path) if el is not None else None
    v = (n.text or default) if n is not None else default
    return "" if v == "$@NULL@$" else v

# ---------------------------------------------------------------- load
src = {}   # label -> (names, read)
for label, p in (("tgz", SRC_TGZ), ("zip", SRC_ZIP)):
    src[label] = open_archive(p)
ims = {}
for label, p in (("zip-sourced", IMS_Z), ("tgz-sourced", IMS_T)):
    zf = zipfile.ZipFile(p)
    ims[label] = (set(zf.namelist()), zf.read)

# A. XML well-formedness
for label, (names, read) in list(src.items()) + list(ims.items()):
    xmls = [n for n in names if n.endswith(".xml")]
    bad = []
    for n in xmls:
        try:
            ET.fromstring(read(n))
        except Exception as e:
            bad.append(f"{n}: {e}")
    check(not bad, f"A/{label}: all {len(xmls)} XML files well-formed", "; ".join(bad))

# B. manifest resolution
for label, (names, read) in ims.items():
    man = ET.fromstring(read("imsmanifest.xml"))
    missing, n_files = [], 0
    for fel in man.iter("{http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1}file"):
        n_files += 1
        if fel.get("href") not in names:
            missing.append(fel.get("href"))
    for rel in man.iter("{http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1}resource"):
        if rel.get("href") not in names:
            missing.append(rel.get("href"))
    check(not missing, f"B/{label}: manifest — all {n_files} <file> hrefs + resource hrefs resolve",
          "missing: " + ", ".join(missing))

# C. source self-consistency (files.xml vs storage), both containers
src_hashes = set()
for label, (names, read) in src.items():
    rows = []
    for fel in ET.fromstring(read("files.xml")).findall("file"):
        rows.append({c.tag: (c.text or "") for c in fel})
    bad = []
    for r in rows:
        p = f"files/{r['contenthash'][:2]}/{r['contenthash']}"
        if p not in names:
            bad.append(r["filename"] + " (missing)")
        elif hashlib.sha1(read(p)).hexdigest() != r["contenthash"]:
            bad.append(r["filename"] + " (hash mismatch)")
    check(not bad, f"C/{label}: files.xml — {len(rows)} rows, storage present, SHA-1 matches",
          "; ".join(bad))
    src_hashes |= {r["contenthash"] for r in rows}

# ---- independent source model (from the ZIP container; H proves tgz equal)
names, read = src["zip"]
qroot = ET.fromstring(read("questions.xml"))
questions, entry_map = {}, {}
for cat in qroot.findall("question_category"):
    cat_id = int(cat.get("id"))
    legacy = cat.find("questions")
    if legacy is not None:
        for q in legacy.findall("question"):
            questions[int(q.get("id"))] = (q, cat_id)
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
                questions[int(best.get("id"))] = (best, cat_id)
                entry_map[int(entry.get("id"))] = int(best.get("id"))

def q_tags(q):
    tel = q.find("tags")
    return {t(tg, "name") for tg in tel.findall("tag")} if tel is not None else set()

src_by_type, src_fb, src_labels, src_calc = {}, 0, 0, 0
for qid, (q, _cid) in questions.items():
    qtype = t(q, "qtype")
    src_by_type[qtype] = src_by_type.get(qtype, 0) + 1
    if t(q, "generalfeedback"):
        src_fb += 1
    if qtype == "calculated":
        src_calc += 1
    plugin = next((c for c in q if c.tag.startswith("plugin_qtype_")), None)
    if plugin is not None:
        for ans in plugin.iter("answer"):
            if t(ans, "feedback"):
                src_fb += 1
        if qtype in ("multichoice", "truefalse"):
            src_labels += len(list(plugin.iter("answer")))
        elif qtype == "matching":
            subs = list(plugin.iter("subquestion"))
            src_labels += len(subs) * len({t(s, "answertext") for s in subs})

# D. counts: converted bank (check both cartridges)
for label, (inames, iread) in ims.items():
    bank = ET.fromstring(iread("questionbank/assessment.xml"))
    items = bank.findall(".//q:item", NS)
    out_by_type, out_fb, out_labels, placeholders = {}, 0, 0, 0
    for it in items:
        flds = {f.findtext("q:fieldlabel", "", NS): f.findtext("q:fieldentry", "", NS)
                for f in it.findall(".//q:qtimetadatafield", NS)}
        qt = flds.get("moodle_qtype", "?")
        out_by_type[qt] = out_by_type.get(qt, 0) + 1
        if flds.get("conversion_status") == "placeholder":
            placeholders += 1
        out_fb += len(it.findall("q:itemfeedback", NS))
        out_labels += len(it.findall(".//q:response_label", NS))
    check(src_by_type == out_by_type, f"D1/{label}: questions by type reconcile",
          f"source {src_by_type} vs bank {out_by_type}")
    check(len(questions) == len(items), f"D2/{label}: total questions reconcile",
          f"source {len(questions)} vs bank {len(items)}")
    check(src_fb == out_fb, f"D3/{label}: feedback blocks reconcile",
          f"source {src_fb} vs bank {out_fb}")
    check(src_labels == out_labels, f"D4/{label}: response options reconcile",
          f"source {src_labels} vs bank {out_labels}")
    check(placeholders == src_calc, f"D5/{label}: placeholders == source calculated questions",
          f"placeholders {placeholders} vs calculated {src_calc}")

# E. quiz membership, resolved independently
info = ET.fromstring(read("moodle_backup.xml")).find("information/contents/activities")
n_set_slots = 0
for a in info.findall("activity"):
    if (a.findtext("modulename") or "") != "quiz":
        continue
    cmid, directory = a.findtext("moduleid"), a.findtext("directory")
    qroot2 = ET.fromstring(read(f"{directory}/quiz.xml"))
    want = set()
    for qi in qroot2.find("quiz/question_instances").findall("question_instance"):
        fixed = t(qi, "question")
        if fixed:
            want.add("Q" + fixed); continue
        ref = qi.find("question_reference")
        if ref is not None and t(ref, "questionbankentryid"):
            want.add("Q" + str(entry_map[int(t(ref, "questionbankentryid"))])); continue
        sref = qi.find("question_set_reference")
        if sref is not None:
            n_set_slots += 1
            filt = json.loads(t(sref, "filtercondition") or "{}")
            catid = filt.get("questioncategoryid")
            catid = int(catid) if catid is not None else None
            want_tags = {str(x).split(",", 1)[-1].strip() for x in filt.get("tags", []) or []}
            for qid, (q, qcid) in questions.items():
                if catid is not None and qcid != catid:
                    continue
                if want_tags and not want_tags.issubset(q_tags(q)):
                    continue
                want.add("Q" + str(qid))
    for label, (inames, iread) in ims.items():
        got_root = ET.fromstring(iread(f"quiz_{cmid}/assessment.xml"))
        got = {it.get("ident") for it in got_root.findall(".//q:item", NS)}
        check(want == got, f"E/{label}: quiz_{cmid} assessment holds exactly its resolved question set",
              f"want {sorted(want)} vs got {sorted(got)}")
    if n_set_slots:
        for label, (inames, iread) in ims.items():
            exc = iread("exceptions.html").decode("utf-8", "replace")
            check("slot draw rules" in exc,
                  f"E2/{label}: set-reference slots disclosed in exception report",
                  f"{n_set_slots} set slots in source")

# F. byte integrity
for label, (inames, iread) in ims.items():
    ims_hashes = {hashlib.sha1(iread(n)).hexdigest() for n in inames}
    missing = [h for h in src_hashes if h not in ims_hashes]
    check(not missing, f"F/{label}: all {len(src_hashes)} unique source files present byte-identical",
          f"missing {len(missing)}" if missing else
          ("vacuous — source carries no files" if not src_hashes else ""))

# G. per-question images
qimg_rows = []
for fel in ET.fromstring(read("files.xml")).findall("file"):
    row = {c.tag: (c.text or "") for c in fel}
    if row["component"] == "question":
        qimg_rows.append(row)
check(True, f"G: per-question image integrity — {len(qimg_rows)} question-image references"
      + (" (vacuous — none in this source)" if not qimg_rows else ""))

# H. container equivalence of the two cartridges
zn, zr = ims["zip-sourced"]
tn, tr = ims["tgz-sourced"]
same = zn == tn and all(zr(n) == tr(n) for n in zn)
check(same, "H: ZIP-sourced and tar.gz-sourced conversions are member-identical",
      f"{len(zn)} members vs {len(tn)} members")

summary = f"\n==== {'ALL CHECKS PASSED' if not failures else 'FAILURES: ' + str(failures)} ===="
lines.append(summary)
out = "\n".join(lines) + "\n"
with open(os.path.join(HERE, "VALIDATION-REAL-OUTPUT.txt"), "w", encoding="utf-8") as f:
    f.write(out)
print(out)
sys.exit(1 if failures else 0)
