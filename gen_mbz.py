# -*- coding: utf-8 -*-
"""
gen_mbz.py — builds a real-structure Moodle backup (.mbz) from course_data.py.

Output: Sample-Course-Moodle-Backup.mbz + assets/ + source-counts.json
Idempotent: the build directory is wiped and rebuilt on every run.
The .mbz layout mirrors a Moodle 4.x course backup taken WITHOUT user data:
  moodle_backup.xml, questions.xml, files.xml, gradebook.xml,
  course/course.xml, sections/section_<id>/{section,inforef}.xml,
  activities/<module>_<cmid>/{<module>,module,inforef,grades}.xml,
  files/<2-char prefix>/<contenthash>   (hashed file storage, as Moodle uses)
"""
import io, os, json, shutil, hashlib, zipfile
from xml.sax.saxutils import escape
from PIL import Image, ImageDraw, ImageFont
import course_data as D

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build_mbz")
ASSETS = os.path.join(HERE, "assets")
MBZ_PATH = os.path.join(HERE, "Sample-Course-Moodle-Backup.mbz")
TS = 1767225600  # fixed timestamp (2026-01-01) so rebuilds are byte-stable in metadata fields

def esc(s):
    return escape(str(s), {'"': "&quot;"})

# ---------------------------------------------------------------- assets
def build_assets():
    os.makedirs(ASSETS, exist_ok=True)
    assets = {}

    # banner.png
    img = Image.new("RGB", (1200, 300), (24, 52, 92))
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 238, 1200, 300], fill=(217, 164, 65))
    try:
        f_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 54)
        f_small = ImageFont.truetype("DejaVuSans.ttf", 30)
    except Exception:
        f_big = f_small = ImageFont.load_default()
    dr.text((60, 80), "Workplace Communication Essentials", fill=(255, 255, 255), font=f_big)
    dr.text((60, 160), "Clear writing  -  useful feedback  -  meetings that decide", fill=(210, 220, 235), font=f_small)
    p = os.path.join(ASSETS, "banner.png"); img.save(p); assets["banner.png"] = p

    # loop-diagram.png
    img = Image.new("RGB", (960, 360), (250, 248, 242))
    dr = ImageDraw.Draw(img)
    boxes = [(40, 130, "SENDER"), (290, 130, "MESSAGE"), (540, 130, "RECEIVER")]
    for x, y, t in boxes:
        dr.rounded_rectangle([x, y, x + 180, y + 90], radius=14, fill=(24, 52, 92))
        dr.text((x + 28, y + 34), t, fill=(255, 255, 255), font=f_small)
    dr.line([225, 175, 285, 175], fill=(60, 60, 60), width=5)
    dr.polygon([(285, 175), (268, 166), (268, 184)], fill=(60, 60, 60))
    dr.line([475, 175, 535, 175], fill=(60, 60, 60), width=5)
    dr.polygon([(535, 175), (518, 166), (518, 184)], fill=(60, 60, 60))
    dr.line([630, 225, 630, 300], fill=(190, 60, 60), width=5)
    dr.line([630, 300, 130, 300], fill=(190, 60, 60), width=5)
    dr.line([130, 300, 130, 228], fill=(190, 60, 60), width=5)
    dr.polygon([(130, 222), (121, 239), (139, 239)], fill=(190, 60, 60))
    dr.text((330, 268), "FEEDBACK", fill=(190, 60, 60), font=f_small)
    dr.text((300, 30), "The communication loop", fill=(24, 52, 92), font=f_big)
    p = os.path.join(ASSETS, "loop-diagram.png"); img.save(p); assets["loop-diagram.png"] = p

    # chart.png — bar chart used inside questions MC08/MC09
    img = Image.new("RGB", (900, 520), (255, 255, 255))
    dr = ImageDraw.Draw(img)
    dr.text((60, 25), "Quick updates: channel staff chose most", fill=(24, 52, 92), font=f_small)
    data = [("Team chat", 46), ("Email", 27), ("Phone call", 17), ("Notice board", 10)]
    y = 90
    for label, val in data:
        dr.text((60, y + 8), label, fill=(40, 40, 40), font=f_small)
        dr.rectangle([280, y, 280 + val * 11, y + 44], fill=(217, 164, 65))
        dr.text((292 + val * 11, y + 8), f"{val}%", fill=(40, 40, 40), font=f_small)
        y += 100
    p = os.path.join(ASSETS, "chart.png"); img.save(p); assets["chart.png"] = p

    # handbook.pdf — two-page image PDF via PIL (a real, valid PDF document)
    pages = []
    for title, lines in [
        ("Course Handbook", ["Workplace Communication Essentials", "",
                             "Page 1 - The communication loop", "",
                             "Sender, message, receiver, feedback.",
                             "Most breakdowns happen at encoding or at feedback.",
                             "Check understanding before you check anything else."]),
        ("Course Handbook (continued)", ["Page 4 - The email to rewrite", "",
                                          "Dear Sir, It has been decided that the",
                                          "submission of reports will henceforth be",
                                          "effectuated on a weekly basis. Please be",
                                          "informed accordingly. (Rewrite this email",
                                          "for the assignment in Section 2.)"]),
    ]:
        pg = Image.new("RGB", (1240, 1754), (255, 255, 255))
        dr = ImageDraw.Draw(pg)
        dr.text((90, 90), title, fill=(24, 52, 92), font=f_big)
        yy = 220
        for ln in lines:
            dr.text((90, yy), ln, fill=(30, 30, 30), font=f_small); yy += 56
        pages.append(pg)
    p = os.path.join(ASSETS, "handbook.pdf")
    pages[0].save(p, "PDF", save_all=True, append_images=pages[1:], resolution=150.0)
    assets["handbook.pdf"] = p

    # checklist.txt
    txt = ("Plain Language Style Checklist\n"
           "1. State the action in the first two lines.\n"
           "2. One topic per message.\n"
           "3. Give a specific deadline, never 'as soon as possible'.\n"
           "4. Replace jargon with common words, or explain it once.\n"
           "5. One idea per sentence.\n"
           "6. Name the owner of every action.\n"
           "7. Read it once as the receiver before sending.\n")
    p = os.path.join(ASSETS, "checklist.txt")
    with open(p, "w", encoding="utf-8") as f: f.write(txt)
    assets["checklist.txt"] = p

    # scorm-missed-deadline.zip — minimal SCORM 1.2 package
    manifest = """<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="MANIFEST_SCORM_WCE" version="1.2"
  xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd
                      http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd
                      http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>1.2</schemaversion>
  </metadata>
  <organizations default="ORG_WCE">
    <organization identifier="ORG_WCE">
      <title>Interactive Scenario: The Missed Deadline</title>
      <item identifier="ITEM_WCE1" identifierref="RES_WCE1" isvisible="true">
        <title>Start the scenario</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES_WCE1" type="webcontent" adlcp:scormtype="sco" href="sco.html">
      <file href="sco.html"/>
    </resource>
  </resources>
</manifest>
"""
    sco = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Interactive Scenario: The Missed Deadline</title></head>
<body>
<h1>The Missed Deadline</h1>
<p>Your team's report reached the client two days late. Your manager asks what happened.</p>
<p>Which opening is most likely to lead to a useful conversation?</p>
<ol>
<li>"The supplier let us down again, it was not our fault." (Blame - the conversation stalls.)</li>
<li>"The report went out on Wednesday instead of Monday. The delay came from my summary
repeating the introduction, so the changes were missed. Next time I will put changes in
bold and confirm receipt." (Observation, effect, fix - the useful opening.)</li>
</ol>
<p><em>End of scenario. In the full course, discuss your choice in the feedback page.</em></p>
<script>
// Minimal SCORM 1.2 run-time hookup: find the API, initialise, mark complete.
(function(){
  function findAPI(w){ var n=0; while(w && !w.API && w.parent && w.parent!==w && n<500){ n++; w=w.parent; } return w ? w.API : null; }
  var api = findAPI(window);
  if(api){ try{ api.LMSInitialize(""); api.LMSSetValue("cmi.core.lesson_status","completed"); api.LMSFinish(""); }catch(e){} }
})();
</script>
</body></html>
"""
    p = os.path.join(ASSETS, "scorm-missed-deadline.zip")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("imsmanifest.xml", manifest)
        z.writestr("sco.html", sco)
    assets["scorm-missed-deadline.zip"] = p
    return assets

MIMETYPES = {".png": "image/png", ".pdf": "application/pdf", ".txt": "text/plain",
             ".zip": "application/zip", ".html": "text/html"}

# ---------------------------------------------------------------- questions
COURSE_ID, COURSE_CTX = 2, 25
CATEGORY_ID = 50
QUESTIONS = []          # filled by build_questions()
QID_BY_NAME = {}

def _answers_xml(answers, start_id):
    """answers: list of (text, fraction, feedback[, tolerance]) -> (xml, next_id, n_feedback)"""
    out, aid, nfb = [], start_id, 0
    for a in answers:
        text, frac, fb = a[0], a[1], a[2]
        tol = f"<tolerance>{a[3]}</tolerance>" if len(a) > 3 else ""
        if fb: nfb += 1
        out.append(f'''<answer id="{aid}">
<answertext>{esc(text)}</answertext>
<answerformat>1</answerformat>
<fraction>{frac:.7f}</fraction>
<feedback>{esc(fb)}</feedback>
<feedbackformat>1</feedbackformat>
{tol}</answer>''')
        aid += 1
    return "\n".join(out), aid, nfb

def build_questions():
    stats = {"by_type": {}, "answers": 0, "answer_feedback": 0, "general_feedback": 0,
             "subquestions": 0}
    qid, aid = 1000, 5000
    xml_parts = []

    def register(qtype, name):
        nonlocal qid
        qid += 1
        QID_BY_NAME[name] = qid
        stats["by_type"][qtype] = stats["by_type"].get(qtype, 0) + 1
        return qid

    def head(q, qtype, name, text, genfb):
        stats["general_feedback"] += 1 if genfb else 0
        return f'''<question id="{q}">
<parent>0</parent>
<name>{esc(name)}</name>
<questiontext>{esc(text)}</questiontext>
<questiontextformat>1</questiontextformat>
<generalfeedback>{esc(genfb)}</generalfeedback>
<generalfeedbackformat>1</generalfeedbackformat>
<defaultgrade>1.0000000</defaultgrade>
<penalty>0.3333333</penalty>
<qtype>{qtype}</qtype>
<length>1</length>
<stamp>samplecourse+260101120000+{q}</stamp>
<timecreated>{TS}</timecreated>
<timemodified>{TS}</timemodified>
<createdby>2</createdby>
<modifiedby>2</modifiedby>
<categoryid>{CATEGORY_ID}</categoryid>
<contextid>{COURSE_CTX}</contextid>'''

    for item in D.MC_SINGLE + D.MC_MULTI:
        name, text, answers, genfb = item[0], item[1], item[2], item[3]
        if len(item) > 4 and item[4]:
            text += f'<p><img src="@@PLUGINFILE@@/{item[4]}" alt="Question image" width="640"></p>'
        single = 1 if item in D.MC_SINGLE else 0
        qtype = "multichoice"
        q = register(qtype, name)
        axml, aid, nfb = _answers_xml(answers, aid)
        stats["answers"] += len(answers); stats["answer_feedback"] += nfb
        xml_parts.append(head(q, qtype, name, text, genfb) + f'''
<plugin_qtype_multichoice_question>
<multichoice>
<id>{q}</id>
<layout>0</layout>
<single>{single}</single>
<shuffleanswers>1</shuffleanswers>
<correctfeedback>Your answer is correct.</correctfeedback>
<correctfeedbackformat>1</correctfeedbackformat>
<partiallycorrectfeedback>Your answer is partially correct.</partiallycorrectfeedback>
<partiallycorrectfeedbackformat>1</partiallycorrectfeedbackformat>
<incorrectfeedback>Your answer is incorrect.</incorrectfeedback>
<incorrectfeedbackformat>1</incorrectfeedbackformat>
<answernumbering>abc</answernumbering>
<shownumcorrect>1</shownumcorrect>
<answers>
{axml}
</answers>
</multichoice>
</plugin_qtype_multichoice_question>
<question_hints>
</question_hints>
</question>''')

    for name, text, is_true, fb_t, fb_f, genfb in D.TRUEFALSE:
        q = register("truefalse", name)
        answers = [("True", 1.0 if is_true else 0.0, fb_t), ("False", 0.0 if is_true else 1.0, fb_f)]
        axml, aid, nfb = _answers_xml(answers, aid)
        stats["answers"] += 2; stats["answer_feedback"] += nfb
        true_id, false_id = aid - 2, aid - 1
        xml_parts.append(head(q, "truefalse", name, text, genfb) + f'''
<plugin_qtype_truefalse_question>
<truefalse>
<id>{q}</id>
<trueanswer>{true_id}</trueanswer>
<falseanswer>{false_id}</falseanswer>
<answers>
{axml}
</answers>
</truefalse>
</plugin_qtype_truefalse_question>
<question_hints>
</question_hints>
</question>''')

    for name, text, answers, genfb in D.SHORTANSWER:
        q = register("shortanswer", name)
        axml, aid, nfb = _answers_xml([(a, f, "") for a, f in answers], aid)
        stats["answers"] += len(answers)
        xml_parts.append(head(q, "shortanswer", name, text, genfb) + f'''
<plugin_qtype_shortanswer_question>
<shortanswer>
<id>{q}</id>
<usecase>0</usecase>
<answers>
{axml}
</answers>
</shortanswer>
</plugin_qtype_shortanswer_question>
<question_hints>
</question_hints>
</question>''')

    for name, text, pairs, genfb in D.MATCHING:
        q = register("matching", name)
        subs, sid = [], 1
        for subq, suba in pairs:
            subs.append(f'''<subquestion id="{sid}">
<questiontext>{esc(subq)}</questiontext>
<questiontextformat>1</questiontextformat>
<answertext>{esc(suba)}</answertext>
</subquestion>''')
            sid += 1
        stats["subquestions"] += len(pairs)
        xml_parts.append(head(q, "matching", name, text, genfb) + f'''
<plugin_qtype_match_question>
<match>
<id>{q}</id>
<shuffleanswers>1</shuffleanswers>
<correctfeedback>Your answer is correct.</correctfeedback>
<correctfeedbackformat>1</correctfeedbackformat>
<partiallycorrectfeedback>Your answer is partially correct.</partiallycorrectfeedback>
<partiallycorrectfeedbackformat>1</partiallycorrectfeedbackformat>
<incorrectfeedback>Your answer is incorrect.</incorrectfeedback>
<incorrectfeedbackformat>1</incorrectfeedbackformat>
<shownumcorrect>1</shownumcorrect>
<subquestions>
{chr(10).join(subs)}
</subquestions>
</match>
</plugin_qtype_match_question>
<question_hints>
</question_hints>
</question>''')

    for name, text, value, tol, genfb in D.NUMERICAL:
        q = register("numerical", name)
        axml, aid, nfb = _answers_xml([(str(value), 1.0, genfb, tol)], aid)
        stats["answers"] += 1; stats["answer_feedback"] += nfb
        xml_parts.append(head(q, "numerical", name, text, genfb) + f'''
<plugin_qtype_numerical_question>
<numerical>
<id>{q}</id>
<answers>
{axml}
</answers>
</numerical>
</plugin_qtype_numerical_question>
<question_hints>
</question_hints>
</question>''')

    for name, text, graderinfo, genfb in D.ESSAY:
        q = register("essay", name)
        xml_parts.append(head(q, "essay", name, text, genfb) + f'''
<plugin_qtype_essay_question>
<essay>
<id>{q}</id>
<responseformat>editor</responseformat>
<responserequired>1</responserequired>
<responsefieldlines>15</responsefieldlines>
<attachments>0</attachments>
<attachmentsrequired>0</attachmentsrequired>
<graderinfo>{esc(graderinfo)}</graderinfo>
<graderinfoformat>1</graderinfoformat>
<responsetemplate></responsetemplate>
</essay>
</plugin_qtype_essay_question>
<question_hints>
</question_hints>
</question>''')

    for name, text, formula, wildcards, genfb in D.CALCULATED:
        q = register("calculated", name)
        axml, aid, nfb = _answers_xml([(formula, 1.0, "", 0.01)], aid)
        stats["answers"] += 1
        dsets = []
        for wname, wmin, wmax, wdec in wildcards:
            items = "\n".join(
                f'<dataset_item><number>{i+1}</number><value>{wmin + i}</value></dataset_item>'
                for i in range(3))
            dsets.append(f'''<dataset_definition>
<category>0</category>
<name>{esc(wname)}</name>
<type>1</type>
<distribution>uniform</distribution>
<minimum>{wmin}</minimum>
<maximum>{wmax}</maximum>
<decimals>{wdec}</decimals>
<itemcount>3</itemcount>
<dataset_items>
{items}
</dataset_items>
<number_of_items>3</number_of_items>
</dataset_definition>''')
        xml_parts.append(head(q, "calculated", name, text, genfb) + f'''
<plugin_qtype_calculated_question>
<calculated>
<id>{q}</id>
<synchronize>0</synchronize>
<answers>
{axml}
</answers>
<dataset_definitions>
{chr(10).join(dsets)}
</dataset_definitions>
</calculated>
</plugin_qtype_calculated_question>
<question_hints>
</question_hints>
</question>''')

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<question_categories>
<question_category id="{CATEGORY_ID}">
<name>Default for {esc(D.COURSE["fullname"])}</name>
<contextid>{COURSE_CTX}</contextid>
<contextlevel>50</contextlevel>
<contextinstanceid>{COURSE_ID}</contextinstanceid>
<info>The default question category for this sample course.</info>
<infoformat>1</infoformat>
<stamp>samplecourse+260101120000+cat</stamp>
<parent>0</parent>
<sortorder>999</sortorder>
<idnumber></idnumber>
<questions>
{chr(10).join(xml_parts)}
</questions>
</question_category>
</question_categories>
'''
    return xml, stats

# ---------------------------------------------------------------- files registry
class FileRegistry:
    def __init__(self):
        self.rows = []          # files.xml rows
        self.physical = {}      # contenthash -> source path
        self._next_id = 0
    def add(self, contextid, component, filearea, itemid, filename, srcpath):
        with open(srcpath, "rb") as f:
            data = f.read()
        h = hashlib.sha1(data).hexdigest()
        self._next_id += 1
        ext = os.path.splitext(filename)[1].lower()
        self.rows.append({
            "id": self._next_id, "contextid": contextid, "component": component,
            "filearea": filearea, "itemid": itemid, "filepath": "/",
            "filename": filename, "filesize": len(data), "contenthash": h,
            "mimetype": MIMETYPES.get(ext, "application/octet-stream"),
            "srcpath": srcpath,
        })
        self.physical.setdefault(h, srcpath)
        return self._next_id
    def xml(self):
        rows = []
        for r in self.rows:
            rows.append(f'''<file>
<id>{r["id"]}</id>
<contextid>{r["contextid"]}</contextid>
<component>{r["component"]}</component>
<filearea>{r["filearea"]}</filearea>
<itemid>{r["itemid"]}</itemid>
<filepath>{r["filepath"]}</filepath>
<filename>{esc(r["filename"])}</filename>
<userid>2</userid>
<filesize>{r["filesize"]}</filesize>
<mimetype>{r["mimetype"]}</mimetype>
<status>0</status>
<timecreated>{TS}</timecreated>
<timemodified>{TS}</timemodified>
<source></source>
<author></author>
<license></license>
<sortorder>0</sortorder>
<repositorytype></repositorytype>
<repositoryid></repositoryid>
<reference></reference>
<contenthash>{r["contenthash"]}</contenthash>
</file>''')
        return ('<?xml version="1.0" encoding="UTF-8"?>\n<files>\n' +
                "\n".join(rows) + "\n</files>\n")

# ---------------------------------------------------------------- activities
def module_xml(cmid, modname, section_id, section_number, instance_id, completion, availability):
    avail = esc(availability) if availability else "$@NULL@$"
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<module id="{cmid}" version="20241007">
<modulename>{modname}</modulename>
<sectionid>{section_id}</sectionid>
<sectionnumber>{section_number}</sectionnumber>
<instance>{instance_id}</instance>
<idnumber></idnumber>
<added>{TS}</added>
<score>0</score>
<indent>0</indent>
<visible>1</visible>
<visibleoncoursepage>1</visibleoncoursepage>
<visibleold>1</visibleold>
<groupmode>0</groupmode>
<groupingid>0</groupingid>
<completion>{completion}</completion>
<completiongradeitemnumber>$@NULL@$</completiongradeitemnumber>
<completionpassgrade>0</completionpassgrade>
<completionview>0</completionview>
<completionexpected>0</completionexpected>
<availability>{avail}</availability>
<showdescription>0</showdescription>
<tags>
</tags>
</module>
'''

def inforef_xml(file_ids=(), qcat_id=None):
    files = "".join(f"<file><id>{i}</id></file>" for i in file_ids)
    qcat = ""
    if qcat_id:
        qcat = (f"<question_categoryref><question_category><id>{qcat_id}</id>"
                f"</question_category></question_categoryref>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<inforef>\n<fileref>\n' +
            files + "\n</fileref>\n" + qcat + "</inforef>\n")

def grades_xml(itemname, modname, instance_id, grademax, sortorder):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<activity_gradebook>
<grade_items>
<grade_item id="{900 + sortorder}">
<categoryid>1</categoryid>
<itemname>{esc(itemname)}</itemname>
<itemtype>mod</itemtype>
<itemmodule>{modname}</itemmodule>
<iteminstance>{instance_id}</iteminstance>
<itemnumber>0</itemnumber>
<idnumber></idnumber>
<gradetype>1</gradetype>
<grademax>{grademax:.5f}</grademax>
<grademin>0.00000</grademin>
<scaleid>0</scaleid>
<outcomeid>0</outcomeid>
<gradepass>0.00000</gradepass>
<multfactor>1.00000</multfactor>
<plusfactor>0.00000</plusfactor>
<aggregationcoef>0.00000</aggregationcoef>
<aggregationcoef2>1.00000</aggregationcoef2>
<sortorder>{sortorder}</sortorder>
<display>0</display>
<decimals>2</decimals>
<hidden>0</hidden>
<locked>0</locked>
<locktime>0</locktime>
<needsupdate>0</needsupdate>
<weightoverride>0</weightoverride>
</grade_item>
</grade_items>
<grade_letters>
</grade_letters>
</activity_gradebook>
'''

def build_backup(assets):
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(BUILD)
    reg = FileRegistry()
    questions_xml, qstats = build_questions()

    # ---- pass 1: assign ids to activities
    acts = []
    cmid = 100
    counters = {}
    cmid_by_name = {}
    for a in D.ACTIVITIES:
        cmid += 1
        counters[a["type"]] = counters.get(a["type"], 0) + 1
        inst = counters[a["type"]]
        section_idx = a["section"]
        acts.append({**a, "cmid": cmid, "instance": inst,
                     "section_id": 10 + section_idx, "ctx": 500 + cmid})
        cmid_by_name[a["name"]] = cmid

    # ---- pass 2: files that belong to questions (image-in-question integrity)
    qimg_files = {}   # question name -> list of file ids
    name_by_qid = {v: k for k, v in QID_BY_NAME.items()}
    for item in D.MC_SINGLE:
        if len(item) > 4 and item[4]:
            qid = QID_BY_NAME[item[0]]
            fid = reg.add(COURSE_CTX, "question", "questiontext", qid, item[4],
                          assets[item[4]])
            qimg_files.setdefault(item[0], []).append(fid)

    # ---- pass 3: activity files + write activity folders
    section_sequences = {11: [], 12: [], 13: [], 14: []}
    backup_activities = []
    counts = {"labels": 0, "pages": 0, "resources": 0, "assignments": 0, "quizzes": 0,
              "prerequisites": 0, "rubric_criteria": 0, "rubric_levels": 0}
    grade_sort = 0

    for a in acts:
        modname = {"page": "page", "label": "label", "resource": "resource",
                   "assign": "assign", "quiz": "quiz"}[a["type"]]
        section_sequences[a["section_id"]].append(a["cmid"])
        folder = os.path.join(BUILD, "activities", f'{modname}_{a["cmid"]}')
        os.makedirs(folder)
        completion = a.get("completion", 0)
        availability = ""
        if a.get("requires"):
            req_cmid = cmid_by_name[a["requires"]]
            availability = json.dumps(
                {"op": "&", "c": [{"type": "completion", "cm": req_cmid, "e": 1}],
                 "showc": [True]}, separators=(",", ":"))
            counts["prerequisites"] += 1
        with open(os.path.join(folder, "module.xml"), "w", encoding="utf-8") as f:
            f.write(module_xml(a["cmid"], modname, a["section_id"], a["section"],
                               a["instance"], completion, availability))
        with open(os.path.join(folder, "roles.xml"), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<roles>\n'
                    '<role_assignments>\n</role_assignments>\n'
                    '<role_overrides>\n</role_overrides>\n</roles>\n')
        file_ids = []
        act_head = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
                    f'<activity id="{a["instance"]}" moduleid="{a["cmid"]}" '
                    f'modulename="{modname}" contextid="{a["ctx"]}">\n')

        if a["type"] == "page":
            counts["pages"] += 1
            content = a["content"]
            for img in ("banner.png", "loop-diagram.png"):
                if f"@@PLUGINFILE@@/{img}" in content:
                    fid = reg.add(a["ctx"], "mod_page", "content", a["instance"],
                                  img, assets[img])
                    file_ids.append(fid)
            body = (f'<page id="{a["instance"]}">\n<name>{esc(a["name"])}</name>\n'
                    f'<intro></intro>\n<introformat>1</introformat>\n'
                    f'<content>{esc(content)}</content>\n<contentformat>1</contentformat>\n'
                    f'<legacyfiles>0</legacyfiles>\n<display>5</display>\n'
                    f'<displayoptions>a:2:{{s:12:"printheading";i:1;s:10:"printintro";i:0;}}</displayoptions>\n'
                    f'<revision>1</revision>\n<timemodified>{TS}</timemodified>\n</page>\n')
            fname = "page.xml"
        elif a["type"] == "label":
            counts["labels"] += 1
            body = (f'<label id="{a["instance"]}">\n<name>{esc(a["name"])}</name>\n'
                    f'<intro>{esc(a["content"])}</intro>\n<introformat>1</introformat>\n'
                    f'<timemodified>{TS}</timemodified>\n</label>\n')
            fname = "label.xml"
        elif a["type"] == "resource":
            counts["resources"] += 1
            src = assets[a["file"]]
            fid = reg.add(a["ctx"], "mod_resource", "content", a["instance"],
                          a["file"], src)
            file_ids.append(fid)
            body = (f'<resource id="{a["instance"]}">\n<name>{esc(a["name"])}</name>\n'
                    f'<intro>{esc(a.get("intro", ""))}</intro>\n<introformat>1</introformat>\n'
                    f'<tobemigrated>0</tobemigrated>\n<legacyfiles>0</legacyfiles>\n'
                    f'<legacyfileslast>0</legacyfileslast>\n<display>0</display>\n'
                    f'<displayoptions>a:1:{{s:10:"printintro";i:1;}}</displayoptions>\n'
                    f'<filterfiles>0</filterfiles>\n</resource>\n')
            fname = "resource.xml"
        elif a["type"] == "assign":
            counts["assignments"] += 1
            body = (f'<assign id="{a["instance"]}">\n<name>{esc(a["name"])}</name>\n'
                    f'<intro>{esc(a["intro"])}</intro>\n<introformat>1</introformat>\n'
                    f'<alwaysshowdescription>1</alwaysshowdescription>\n'
                    f'<submissiondrafts>0</submissiondrafts>\n<requiresubmissionstatement>0</requiresubmissionstatement>\n'
                    f'<sendnotifications>0</sendnotifications>\n<duedate>{TS + 1209600}</duedate>\n'
                    f'<allowsubmissionsfromdate>{TS}</allowsubmissionsfromdate>\n<grade>100</grade>\n'
                    f'<timemodified>{TS}</timemodified>\n<submissionplugins>onlinetext</submissionplugins>\n</assign>\n')
            fname = "assign.xml"
            # grading.xml — rubric definition (gradingform_rubric backup structure)
            crit_xml, lev_total = [], 0
            for ci, (crit, levels) in enumerate(a["rubric"], start=1):
                lev_xml = []
                for li, lev in enumerate(levels):
                    lev_total += 1
                    lev_xml.append(
                        f'<level id="{ci * 10 + li}"><criterionid>{ci}</criterionid>'
                        f'<score>{li}.00000</score><definition>{esc(lev)}</definition>'
                        f'<definitionformat>1</definitionformat></level>')
                crit_xml.append(
                    f'<rubric_criterion id="{ci}"><sortorder>{ci}</sortorder>'
                    f'<description>{esc(crit)}</description><descriptionformat>1</descriptionformat>'
                    f'<levels>{"".join(lev_xml)}</levels></rubric_criterion>')
            counts["rubric_criteria"] += len(a["rubric"]); counts["rubric_levels"] += lev_total
            grading = ('<?xml version="1.0" encoding="UTF-8"?>\n<grading>\n<areas>\n'
                       '<area id="1">\n<areaname>submissions</areaname>\n<activemethod>rubric</activemethod>\n'
                       '<definitions>\n<definition id="1">\n<type>rubric</type>\n'
                       '<name>Email rewrite rubric</name>\n<description></description>\n'
                       '<descriptionformat>1</descriptionformat>\n<status>20</status>\n'
                       f'<timecopied>0</timecopied>\n<timecreated>{TS}</timecreated>\n<timemodified>{TS}</timemodified>\n'
                       '<usercreated>2</usercreated>\n<usermodified>2</usermodified>\n'
                       '<options>a:1:{s:13:"sortlevelsasc";i:1;}</options>\n'
                       '<rubric><rubric_criteria>' + "".join(crit_xml) +
                       '</rubric_criteria></rubric>\n</definition>\n</definitions>\n</area>\n</areas>\n</grading>\n')
            with open(os.path.join(folder, "grading.xml"), "w", encoding="utf-8") as f:
                f.write(grading)
            grade_sort += 1
            with open(os.path.join(folder, "grades.xml"), "w", encoding="utf-8") as f:
                f.write(grades_xml(a["name"], "assign", a["instance"], 100, grade_sort))
        elif a["type"] == "quiz":
            counts["quizzes"] += 1
            members = D.QUIZ_MEMBERSHIP[a["question_names"]]
            inst_xml = []
            for qi, qname in enumerate(members, start=1):
                inst_xml.append(
                    f'<question_instance id="{qi}"><question>{QID_BY_NAME[qname]}</question>'
                    f'<grade>1.0000000</grade></question_instance>')
            body = (f'<quiz id="{a["instance"]}">\n<name>{esc(a["name"])}</name>\n'
                    f'<intro>{esc(a.get("intro", ""))}</intro>\n<introformat>1</introformat>\n'
                    f'<timeopen>0</timeopen>\n<timeclose>0</timeclose>\n<timelimit>0</timelimit>\n'
                    f'<overduehandling>autosubmit</overduehandling>\n<graceperiod>0</graceperiod>\n'
                    f'<preferredbehaviour>deferredfeedback</preferredbehaviour>\n<canredoquestions>0</canredoquestions>\n'
                    f'<attempts_number>0</attempts_number>\n<attemptonlast>0</attemptonlast>\n'
                    f'<grademethod>1</grademethod>\n<decimalpoints>2</decimalpoints>\n'
                    f'<questiondecimalpoints>-1</questiondecimalpoints>\n<shuffleanswers>1</shuffleanswers>\n'
                    f'<sumgrades>{len(members)}.0000000</sumgrades>\n<grade>{len(members)}.0000000</grade>\n'
                    f'<timecreated>{TS}</timecreated>\n<timemodified>{TS}</timemodified>\n'
                    f'<password></password>\n<subnet></subnet>\n<browsersecurity></browsersecurity>\n'
                    f'<delay1>0</delay1>\n<delay2>0</delay2>\n<showuserpicture>0</showuserpicture>\n'
                    f'<showblocks>0</showblocks>\n<completionattemptsexhausted>0</completionattemptsexhausted>\n'
                    f'<completionminattempts>0</completionminattempts>\n<navmethod>free</navmethod>\n'
                    f'<question_instances>\n' + "\n".join(inst_xml) + '\n</question_instances>\n</quiz>\n')
            fname = "quiz.xml"
            grade_sort += 1
            with open(os.path.join(folder, "grades.xml"), "w", encoding="utf-8") as f:
                f.write(grades_xml(a["name"], "quiz", a["instance"], len(members), grade_sort))

        with open(os.path.join(folder, fname), "w", encoding="utf-8") as f:
            f.write(act_head + body + "</activity>\n")
        qcat = CATEGORY_ID if a["type"] == "quiz" else None
        with open(os.path.join(folder, "inforef.xml"), "w", encoding="utf-8") as f:
            f.write(inforef_xml(file_ids, qcat))
        backup_activities.append((a, modname))

    # ---- sections
    for idx, s in enumerate(D.SECTIONS, start=1):
        sid = 10 + idx
        folder = os.path.join(BUILD, "sections", f"section_{sid}")
        os.makedirs(folder)
        seq = ",".join(str(c) for c in section_sequences[sid])
        with open(os.path.join(folder, "section.xml"), "w", encoding="utf-8") as f:
            f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<section id="{sid}">
<number>{idx}</number>
<name>{esc(s["name"])}</name>
<summary>{esc(s["summary"])}</summary>
<summaryformat>1</summaryformat>
<sequence>{seq}</sequence>
<visible>1</visible>
<availabilityjson>{{"op":"&amp;","c":[],"showc":[]}}</availabilityjson>
<component></component>
<itemid>0</itemid>
</section>
''')
        with open(os.path.join(folder, "inforef.xml"), "w", encoding="utf-8") as f:
            f.write(inforef_xml())

    # ---- course/course.xml
    os.makedirs(os.path.join(BUILD, "course"))
    with open(os.path.join(BUILD, "course", "course.xml"), "w", encoding="utf-8") as f:
        f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<course id="{COURSE_ID}" contextid="{COURSE_CTX}">
<shortname>{esc(D.COURSE["shortname"])}</shortname>
<fullname>{esc(D.COURSE["fullname"])}</fullname>
<idnumber></idnumber>
<summary>{esc(D.COURSE["summary"])}</summary>
<summaryformat>1</summaryformat>
<format>topics</format>
<showgrades>1</showgrades>
<newsitems>5</newsitems>
<startdate>{TS}</startdate>
<enddate>0</enddate>
<marker>0</marker>
<maxbytes>0</maxbytes>
<legacyfiles>0</legacyfiles>
<showreports>0</showreports>
<visible>1</visible>
<groupmode>0</groupmode>
<groupmodeforce>0</groupmodeforce>
<defaultgroupingid>0</defaultgroupingid>
<lang></lang>
<forcetheme></forcetheme>
<timecreated>{TS}</timecreated>
<timemodified>{TS}</timemodified>
<requested>0</requested>
<enablecompletion>1</enablecompletion>
<completionnotify>0</completionnotify>
<hiddensections>0</hiddensections>
<category id="1">
<name>Miscellaneous</name>
</category>
<tags>
</tags>
<customfields>
</customfields>
</course>
''')

    # ---- remaining root/course files a real backup always carries
    for fname, body in [
        ("groups.xml", "<groups>\n</groups>\n"),
        ("scales.xml", "<scales_definition>\n</scales_definition>\n"),
        ("outcomes.xml", "<outcomes_definition>\n</outcomes_definition>\n"),
    ]:
        with open(os.path.join(BUILD, fname), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + body)
    for fname, body in [
        ("roles.xml", "<roles>\n<role_assignments>\n</role_assignments>\n"
                      "<role_overrides>\n</role_overrides>\n</roles>\n"),
        ("competencies.xml", "<course_competencies>\n<settings>\n</settings>\n"
                             "<competencies>\n</competencies>\n</course_competencies>\n"),
        ("completiondefaults.xml", "<course_completion_defaults>\n"
                                   "</course_completion_defaults>\n"),
    ]:
        with open(os.path.join(BUILD, "course", fname), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + body)

    # ---- gradebook.xml (course level)
    with open(os.path.join(BUILD, "gradebook.xml"), "w", encoding="utf-8") as f:
        f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<gradebook>
<attributes>
</attributes>
<grade_categories>
<grade_category id="1">
<parent>0</parent>
<depth>1</depth>
<path>/1/</path>
<fullname>?</fullname>
<aggregation>13</aggregation>
<keephigh>0</keephigh>
<droplow>0</droplow>
<aggregateonlygraded>1</aggregateonlygraded>
<aggregateoutcomes>0</aggregateoutcomes>
<timecreated>{TS}</timecreated>
<timemodified>{TS}</timemodified>
<hidden>0</hidden>
</grade_category>
</grade_categories>
<grade_items>
<grade_item id="1">
<categoryid>1</categoryid>
<itemname></itemname>
<itemtype>course</itemtype>
<itemmodule></itemmodule>
<iteminstance>0</iteminstance>
<itemnumber>0</itemnumber>
<gradetype>1</gradetype>
<grademax>40.00000</grademax>
<grademin>0.00000</grademin>
</grade_item>
</grade_items>
<grade_letters>
</grade_letters>
<grade_settings>
<grade_setting>
<name>minmaxtouse</name>
<value>1</value>
</grade_setting>
</grade_settings>
</gradebook>
''')

    # ---- files.xml + physical storage
    with open(os.path.join(BUILD, "files.xml"), "w", encoding="utf-8") as f:
        f.write(reg.xml())
    for h, src in reg.physical.items():
        dest = os.path.join(BUILD, "files", h[:2], h)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)

    # ---- questions.xml
    with open(os.path.join(BUILD, "questions.xml"), "w", encoding="utf-8") as f:
        f.write(questions_xml)

    # ---- roles.xml (restore requires this file; standard archetype roles)
    def _caps(pairs):
        return "".join(
            f'<capability><name>{n}</name><permission>{p}</permission>'
            f'<timemodified>{TS}</timemodified><modifierid>2</modifierid></capability>'
            for n, p in pairs)
    roles_defs = [
        (3, "Teacher", "editingteacher", "editingteacher", 3,
         [("moodle/course:view", 1), ("moodle/course:update", 1),
          ("moodle/course:manageactivities", 1), ("mod/quiz:attempt", 1)]),
        (4, "Non-editing teacher", "teacher", "teacher", 4,
         [("moodle/course:view", 1), ("mod/quiz:attempt", 1), ("mod/quiz:reviewmyattempts", 1)]),
        (5, "", "student", "student", 5,
         [("moodle/course:view", 1), ("mod/quiz:attempt", 1), ("mod/assign:submit", 1)]),
    ]
    role_xml = []
    for rid_, rname, short, arch, sortorder, caps in roles_defs:
        role_xml.append(f'''<role id="{rid_}">
<name>{esc(rname)}</name>
<shortname>{short}</shortname>
<nameincourse>$@NULL@$</nameincourse>
<description></description>
<sortorder>{sortorder}</sortorder>
<archetype>{arch}</archetype>
<contextlevels>
<contextlevel>50</contextlevel>
<contextlevel>70</contextlevel>
<contextlevel>80</contextlevel>
</contextlevels>
<allowassign>
</allowassign>
<allowoverride>
</allowoverride>
<allowswitch>
</allowswitch>
<allowview>
</allowview>
<capabilities>
{_caps(caps)}
</capabilities>
</role>''')
    with open(os.path.join(BUILD, "roles.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<roles>\n' +
                "\n".join(role_xml) + "\n</roles>\n")

    # ---- moodle_backup.xml
    act_entries, sec_entries = [], []
    for a, modname in backup_activities:
        act_entries.append(
            f'<activity><moduleid>{a["cmid"]}</moduleid><sectionid>{a["section_id"]}</sectionid>'
            f'<modulename>{modname}</modulename><title>{esc(a["name"])}</title>'
            f'<directory>activities/{modname}_{a["cmid"]}</directory></activity>')
    for idx, s in enumerate(D.SECTIONS, start=1):
        sec_entries.append(
            f'<section><sectionid>{10 + idx}</sectionid><title>{esc(s["name"])}</title>'
            f'<directory>sections/section_{10 + idx}</directory></section>')
    root_settings = [("filename", "backup-wce101.mbz"), ("users", "0"), ("anonymize", "0"),
                     ("role_assignments", "0"), ("activities", "1"), ("blocks", "0"),
                     ("files", "1"), ("filters", "0"), ("comments", "0"), ("badges", "0"),
                     ("calendarevents", "0"), ("userscompletion", "0"), ("logs", "0"),
                     ("grade_histories", "0"), ("groups", "0"), ("competencies", "0"),
                     ("customfield", "0"), ("contentbankcontent", "0"),
                     ("legacyfiles", "0")]
    parts = [f'<setting><level>course</level><name>{n}</name><value>{v}</value></setting>'
             for n, v in root_settings]
    for idx in range(1, len(D.SECTIONS) + 1):
        parts.append(f'<setting><level>section</level><section>section_{10 + idx}</section>'
                     f'<name>section_included</name><value>1</value></setting>')
        parts.append(f'<setting><level>section</level><section>section_{10 + idx}</section>'
                     f'<name>userinfo</name><value>0</value></setting>')
    for a, modname in backup_activities:
        parts.append(f'<setting><level>activity</level><activity>{modname}_{a["cmid"]}</activity>'
                     f'<name>activity_included</name><value>1</value></setting>')
        parts.append(f'<setting><level>activity</level><activity>{modname}_{a["cmid"]}</activity>'
                     f'<name>userinfo</name><value>0</value></setting>')
    set_xml = "".join(parts)
    with open(os.path.join(BUILD, "moodle_backup.xml"), "w", encoding="utf-8") as f:
        f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<moodle_backup>
<information>
<name>backup-moodle2-course-{COURSE_ID}-{D.COURSE["shortname"].lower()}.mbz</name>
<moodle_version>2024100715</moodle_version>
<moodle_release>4.5.3</moodle_release>
<backup_version>2024100715</backup_version>
<backup_release>4.5</backup_release>
<backup_date>{TS}</backup_date>
<mnet_remoteusers>0</mnet_remoteusers>
<include_files>1</include_files>
<include_file_references_to_external_content>0</include_file_references_to_external_content>
<original_wwwroot>https://example.invalid</original_wwwroot>
<original_site_identifier_hash>sample</original_site_identifier_hash>
<original_course_id>{COURSE_ID}</original_course_id>
<original_course_format>topics</original_course_format>
<original_course_fullname>{esc(D.COURSE["fullname"])}</original_course_fullname>
<original_course_shortname>{esc(D.COURSE["shortname"])}</original_course_shortname>
<original_course_startdate>{TS}</original_course_startdate>
<original_course_enddate>0</original_course_enddate>
<original_course_contextid>{COURSE_CTX}</original_course_contextid>
<original_system_contextid>1</original_system_contextid>
<details>
<detail backupid="samplebackupwce101">
<type>course</type>
<format>moodle2</format>
<interactive>0</interactive>
<mode>10</mode>
<execution>1</execution>
<executiontime>0</executiontime>
</detail>
</details>
<settings>
{set_xml}
</settings>
<contents>
<activities>
{chr(10).join(act_entries)}
</activities>
<sections>
{chr(10).join(sec_entries)}
</sections>
<course>
<courseid>{COURSE_ID}</courseid>
<title>{esc(D.COURSE["fullname"])}</title>
<contextid>{COURSE_CTX}</contextid>
</course>
</contents>
</information>
</moodle_backup>
''')

    # ---- zip into .mbz (paths relative to build root)
    if os.path.exists(MBZ_PATH):
        os.remove(MBZ_PATH)
    with zipfile.ZipFile(MBZ_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(BUILD):
            for fn in sorted(files):
                full = os.path.join(root, fn)
                z.write(full, os.path.relpath(full, BUILD))

    counts.update({
        "sections": len(D.SECTIONS),
        "activities_total": len(acts),
        "files_rows_total": len(reg.rows),
        "files_unique_physical": len(reg.physical),
        "images_unique": len({r["contenthash"] for r in reg.rows
                              if r["mimetype"] == "image/png"}),
        "questions_total": sum(qstats["by_type"].values()),
        "questions_by_type": qstats["by_type"],
        "answers_total": qstats["answers"],
        "matching_subquestions": qstats["subquestions"],
        "feedback_answer_level": qstats["answer_feedback"],
        "feedback_question_level": qstats["general_feedback"],
        "feedback_total": qstats["answer_feedback"] + qstats["general_feedback"],
        "quiz_memberships": {k: len(v) for k, v in D.QUIZ_MEMBERSHIP.items()},
        "question_image_files": {k: len(v) for k, v in qimg_files.items()},
    })
    with open(os.path.join(HERE, "source-counts.json"), "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=2)
    print(json.dumps(counts, indent=2))
    print("MBZ:", MBZ_PATH, os.path.getsize(MBZ_PATH), "bytes")

if __name__ == "__main__":
    assets = build_assets()
    build_backup(assets)
    print("DONE")
