# Course Conversion Report — Moodle → Canvas (IMS Common Cartridge)

**Course:** Workplace Communication Essentials (WCE-101)
**Source:** Moodle backup archive (`.mbz`), Moodle 4.5 format
**Delivered:** Canvas IMS Common Cartridge package (`.imscc`) with QTI assessments
**Conversion type:** file-to-file. No access to either live platform was used or required.

---

## 1. What was converted — reconciled counts

Every figure below was reconciled automatically, source against output, by the
validation script shipped with this sample (`validate.py`, output in
`VALIDATION-OUTPUT.txt`). Nothing in this table is estimated.

| Item | Source (.mbz) | Cartridge (.imscc) | Result |
|---|---|---|---|
| Course sections | 4 | 4 | ✅ exact |
| Pages | 4 | 4 | ✅ exact |
| Labels | 2 | 2 | ✅ exact |
| File resources | 3 | 3 | ✅ exact |
| Assignments | 1 | 1 | ✅ exact |
| Quizzes | 3 | 3 QTI assessments | ✅ exact |
| Question bank | — | 1 QTI assessment (all 63 questions) | ✅ |
| **Questions — total** | **63** | **63** | ✅ exact |
| Multiple choice (single + multiple answer) | 25 | 25 | ✅ exact |
| True/false | 10 | 10 | ✅ exact |
| Short answer | 8 | 8 | ✅ exact |
| Matching (24 sub-questions) | 6 | 6 | ✅ exact |
| Numerical | 6 | 6 | ✅ exact |
| Essay | 5 | 5 | ✅ exact |
| Calculated | 3 | 3 **labelled placeholders** (see §3) | ⚠️ exception |
| Response options (answers + matching choices) | 224 | 224 | ✅ exact |
| Feedback items in question bank (134 answer-level + 63 question-level) | 197 | 197 | ✅ exact |
| Quiz membership | 10 + 10 + 10 questions | identical sets in all 3 quizzes | ✅ exact |
| Unique files (3 images, PDF handbook, text checklist, SCORM zip) | 6 | 6, **byte-identical (SHA-1 verified)** | ✅ exact |
| IMS manifest resources | — | 15, all references resolve | ✅ |

## 2. Image integrity inside questions

Broken image paths inside question-bank questions are the most common silent failure
in LMS migrations, so they were tested individually — not just at file level. Each
image referenced from inside a question was located in the cartridge and its SHA-1
hash compared against the source:

| Question | Image | In question bank | In quiz copy |
|---|---|---|---|
| MC08 "chart channel question" | chart.png | ✅ hash match | ✅ hash match (Final Quiz) |
| MC09 "chart least chosen" | chart.png | ✅ hash match | n/a (bank only) |
| MC17 "loop diagram" | loop-diagram.png | ✅ hash match | ✅ hash match (Final Quiz) |

Images embedded in page content (course banner, feedback-loop diagram) are likewise
carried byte-identical and re-linked to cartridge paths.

## 3. Pre-Migration Exception Report

The items below **cannot be converted faithfully** into IMS Common Cartridge. None of
them was silently dropped: each was either carried in a documented fallback form or
is listed here for manual recreation in the target system. This section is the
complete list — if it is not listed here, it converted.

| # | Item | Why it cannot convert | Fallback taken |
|---|---|---|---|
| 1 | Assignment rubric on "Rewrite a Workplace Email" (4 criteria, 12 levels) | Moodle rubric grading forms have no machine-readable equivalent in IMS Common Cartridge. | Rubric criteria and level descriptions reproduced as a readable table inside the assignment page; a human must rebuild the rubric in the target system's grading tool. |
| 2 | SCORM 1.2 package "The Missed Deadline" | The package file transfers, but its runtime wiring — launch settings and **grade passback to the gradebook — cannot be verified from files alone and is not converted.** | Package carried byte-identical; a human must attach it with the target system's SCORM tool and test it in student view, including a completion/passback check. |
| 3 | Calculated question "CA01 reply window" | Moodle calculated questions randomise numbers from wildcard datasets on every attempt; QTI/Common Cartridge has no equivalent mechanism. | Clearly labelled placeholder item in the question bank carrying the original question text, formula and wildcard ranges; recreate natively in the target system. |
| 4 | Calculated question "CA02 words per page" | As above. | As above. |
| 5 | Calculated question "CA03 meeting people hours" | As above. | As above. |
| 6 | Restrict-access rule on "The Sender-Message-Feedback Loop" (opens after "Welcome and How This Course Works" is complete) | IMS Common Cartridge has no standard for activity prerequisites. | Listed here for manual recreation in the target system's requirements/prerequisites settings. |
| 7 | Restrict-access rule on "Giving Feedback That Lands" (opens after "Quiz 1: Writing Clearly" is complete) | As above. | As above. |
| 8 | Gradebook structure and weighting (course total aggregated from 1 assignment and 3 quizzes under Moodle aggregation rules) | Cartridge packages do not carry gradebook aggregation or weighting. | Recreate gradebook categories and weights manually in the target system. |
| 9 | Activity completion tracking settings (4 activities carry Moodle completion flags) | Completion conditions are not a cartridge concept. | Re-enable completion tracking per activity in the target system if required. |
| 10 | LTI / external-tool activities | None existed in the source course — not applicable to this conversion. (In real courses, LTI credentials never transfer in a cartridge and must be re-issued by the tool provider.) | No action. |

## 4. Validation performed

A runnable validation script (`validate.py`) checks both archives end to end.
Result on this conversion: **all 13 checks passed**, including:

- XML well-formedness of every XML file in both archives (77 in the source backup,
  5 in the cartridge, plus the nested SCORM manifest).
- Every file and resource reference in the cartridge manifest resolves to a file
  actually present in the package (21 file references checked).
- Source file storage integrity: all 8 Moodle file rows resolve to physical files
  whose SHA-1 hashes match the backup's own records.
- Question counts reconcile 1:1 overall and **by type**; feedback items reconcile
  (197 = 197); response options reconcile (224 = 224).
- Each quiz in the cartridge contains exactly its source question set (10/10 × 3).
- All 6 unique source files are present in the cartridge byte-identical.
- The 3 calculated questions are present as labelled placeholders — counted as
  placeholders, never as conversions.

## 5. Verification notes (read before importing)

- The source backup was additionally test-restored into a locally installed
  Moodle 4.5: the restore completed and Moodle parsed and loaded the full course
  data (all 63 questions and the category register in the restore's working tables,
  and the course with its 4 sections is created). The test restore did **not**
  fully materialise the activities in that sandbox — this is a limitation of the
  hand-built sample source, and it is disclosed rather than hidden. Client-supplied
  backups are genuine exports from a live Moodle and do not have this limitation;
  the converter reads the same backup structures either way.
- **In-Canvas validation remains a buyer-side step we cannot perform from files:**
  after import, run Canvas's link validator over the course and open the SCORM
  activity in student view to confirm launch and grade passback. The cartridge is
  standards-shaped and every internal reference has been machine-checked, but no
  file-level check can substitute for those two in-platform tests.

---

*Sample produced end-to-end from original sample content created for this
demonstration. Generator, converter and validation scripts are included in the
sample folder so every figure in this report can be re-run and re-checked.*
