# REAL-EXPORT TEST — converter vs a genuine Moodle-produced backup

**Date: 2026-10-24. Local test only; nothing pitched or sent anywhere.**
Companion to `../VERDICT.md` (which now carries a short addendum pointing here).

## Why this test exists

The original proof sample converted a **hand-built** .mbz. The disclosed gap:
the converter had never been run against a file that a real Moodle actually
wrote — and real client jobs always start from genuine Moodle exports. This
test closes that question with evidence.

## The genuine export

Produced 2026-10-24 by the locally installed **Moodle 4.5.15+ (PHP 8.3 +
MariaDB 10.11)** using Moodle's own CLI backup
(`admin/cli/backup.php --courseid=11`), exporting the restored fixture course
(course id 11, "fixture" — Moodle's shipped 3.11 quiz fixture, restored into
this 4.5 install during the original sample work; the export file itself is
100% written by Moodle 4.5's backup code).

Two genuine containers of the same course were tested, because Moodle's
`mbz_packer` writes **tar.gz by default** (confirmed in
`lib/filestorage/mbz_packer.php`: ZIP only when the site sets
`$CFG->usezipbackups`; even Moodle 3.11's shipped fixture is gzip):

- `genuine/backup-moodle2-course-11-fixture-20261024-1246.mbz` — tar.gz, 6,136 bytes (the default).
- `genuine-zip/backup-moodle2-course-11-fixture-20261024-1247.mbz` — ZIP, 12,819 bytes
  (produced with `usezipbackups` temporarily set via CLI, then deleted again
  and caches purged — the install was left exactly as found).

### Exact contents of the genuine export

| Construct | Count / detail |
|---|---|
| Sections | 2 — id 16 (number 0, unnamed, empty sequence), id 17 (number 1, unnamed, sequence = the quiz) |
| Activities | 1 — quiz "moodle_311_quiz" (moduleid 1, in section 17) |
| Question categories | 3 — two empty "top" categories (ids 4, 6) + "Default for moodle_311_quiz" (id 5) |
| Question bank entries | 2, one version each |
| Questions | **2, both `truefalse`** — Q1 "First question" (tags: *first question, one, number one*), Q2 "Second question" (tags: *one, number one, second question*) |
| Answers | 4 (2 per question) |
| Feedback texts | 0 (general and answer-level all empty) |
| Files (`files.xml`) | **0 rows** — the course carries no files or images |
| Gradebook | 1 grade item |
| Quiz slots | **3, all `question_set_reference`** (random/filter draws): slots 1–2 filter on category 5 + Q1's exact tag set; slot 3 on category 5 + Q2's exact tag set |

Size honesty: this is a **thin** course. All 15 `.mbz` fixtures shipped with
Moodle were scanned — they are almost all truefalse-centric test fixtures; no
richer genuine course (multichoice, files, fixed slots) was available in the
install without sinking the task into new course authoring. What this test
does and does not prove is scoped accordingly below.

## Converter BEFORE fixes — total failure on genuine files

Run unmodified (copies in `run1_tgz_unmodified/` and `run2_zip_unmodified/`):

- **tar.gz (the default genuine container):** crashed at open —
  `zipfile.BadZipFile: File is not a zip file`. Converted: nothing.
- **ZIP variant:** opened, then crashed in `load_questions` —
  `AttributeError: 'NoneType' object has no attribute 'findall'` (it read only
  the first question category — an empty "top" — and assumed the pre-4.0
  `<questions>` layout). Converted: nothing.

## Fixes applied to `convert_mbz_to_imscc.py` (all disclosed, all generalising)

- **F1 — Container sniffing.** Archive opened by magic bytes (gzip → tar.gz,
  PK → ZIP), mirroring Moodle's own restore. The original assumed ZIP always.
- **F2 — `$@NULL@$` normalisation.** `txt()` now treats Moodle's NULL literal
  as empty; the original crashed on `int("$@NULL@$")` in a real section
  sequence.
- **F3 — Question-bank layout.** `load_questions()` walks **all** categories
  and supports the Moodle 4.x layout (bank entries → versions → questions;
  highest version per entry converted) as well as the legacy pre-4.0 layout.
  Records each question's category id and tags, and builds a
  bank-entry → question map.
- **F4 — Quiz slot resolution.** New `resolve_quiz_members()` handles all
  three slot forms: legacy fixed `<question>`, 4.x `<question_reference>`
  (via the bank-entry map), and `<question_set_reference>` — the JSON filter
  (category + tag-superset match) resolves to **all candidate questions**,
  and the draw is disclosed in the exception report instead of being faked
  as fixed membership.
- **F5 — Sections.** Uses each section's own `<directory>` from the backup
  index; display title falls back name → non-numeric index title →
  "Section N" (genuine unnamed sections put the bare number in the index).
- **F6 — Gradebook exception de-hardcoded.** The original text asserted
  sample-specific numbers ("course total 40 points… 1 assignment (100),
  3 quizzes (10 each)") — false on any real file. It now derives the grade
  item count from the actual `gradebook.xml`. (Note: the old text did not
  even match the sample file itself, whose `gradebook.xml` holds exactly
  1 `<grade_item>` element.)
- **F7 — Completion exception de-hardcoded.** "4 source activities" replaced
  by a count of real completion flags in the activities' `module.xml`.
- **F8 — Manifest identifiers.** `MANIFEST_WCE101`/`ORG_WCE101` were
  hardcoded to the sample course; now derived from the source shortname.
- **F9 — Exotic question types.** Unknown qtypes (random, cloze, drag-drop…)
  used to raise and kill the whole run; they now degrade to a labelled
  placeholder item + exception entry — never a silent drop, never a crash.
- **F10 — Unhandled activity modules.** Forum/glossary/lesson/etc. used to
  leave an organisation item pointing at a resource that was never created;
  they now get a labelled placeholder page + exception entry, and a missing
  activity XML no longer crashes the lookup.

## Converter AFTER fixes — identical success on both genuine containers

Exit 0 on both; the two cartridges are **member-identical** (validation
check H). Cartridge: 3,508 bytes, 4 members (`imsmanifest.xml`,
`quiz_1/assessment.xml`, `questionbank/assessment.xml`, `exceptions.html`).

- Sections: 2 (titled "Section 0" / "Section 1" — honest fallbacks for
  unnamed sections). Resources: 3. Quizzes: 1. Assessments written: 2.
- Bank: 2 items, both truefalse. Quiz assessment: exactly {Q1, Q2} — the two
  tag-filter candidates. QTI response labels: 8 total (4 per assessment).
  Feedback blocks: 0 (source has none). Placeholders: 0.
- Exceptions (4, all file-derived): quiz slot draw rules (3 set slots,
  2 candidates, 0 unresolved); gradebook (1 grade item); completion
  (1 activity carries tracking); LTI note (none present in source).

## Validation — `validate_real.py` (26 checks, ALL PASS)

Sibling of `../validate.py`, same independent-recount approach, adapted to
genuine-export constructs. Full output: `VALIDATION-REAL-OUTPUT.txt`.

- **A** XML well-formedness: 38 XML files in each source container, 3 in each
  cartridge — all well-formed.
- **B** Manifest resolution: every `<file>`/resource href resolves, both
  cartridges.
- **C** Source self-consistency: `files.xml` ↔ storage SHA-1 (0 rows in this
  export).
- **D** Count reconciliation: questions by type {truefalse: 2} = bank,
  totals 2 = 2, feedback 0 = 0, response options 4 = 4, placeholders 0 =
  calculated 0 — for both cartridges.
- **E** Quiz membership: independently re-resolved slot set {Q1, Q2} equals
  the quiz assessment item set, both cartridges; **E2**: set-reference slots
  are disclosed in `exceptions.html`.
- **F/G** Byte integrity / per-question images: **vacuous** — the genuine
  source carries no files and no question images (stated, not hidden).
- **H** The tar.gz-sourced and ZIP-sourced conversions are member-identical.

## Regression — original sample unaffected

The fixed converter re-run on the original hand-built sample: **every
conversion count identical to pre-fix**, exceptions still 10, and
`validate.py` still reports **ALL CHECKS PASSED (13/13)**. The only output
change anywhere is the gradebook exception wording (F6, now file-derived).

## Updated verdict on the gap

**CLOSED for the commercially decisive direction.** The converter now
provably consumes genuine Moodle output — both containers Moodle produces,
the 4.x question-bank layout, NULL-literal fields, unnamed sections, and
random/filter quiz slots — end-to-end, with independent validation. Real
client files, not our imitation of them, are now a tested input. The
hand-built source's own live-restore quirk (see `../MOODLE-RESTORE-LOG.md`)
remains open but is commercially moot for the file-in/file-out service as
sold; it would matter only if a job required *us* to restore a backup into a
live Moodle.

**Still open (narrowed, honestly):**
- Genuine-file coverage here is thin by necessity: only quiz + truefalse +
  set-reference slots were exercised on genuine files. Page/label/resource/
  assign activities and the other six question types remain proven on the
  hand-built sample and its 13-check suite, not on genuine exports.
- Fixed `<question_reference>` slots and multi-version bank entries are
  implemented (F3/F4) but were **not exercised** by a genuine file in this
  test (the fixture used set references; entries had single versions).
- Unhandled-module placeholders (F10) are implemented but not exercised on a
  genuine file here (this course has no forum/glossary/etc.).
- Unchanged from the original verdict: in-Canvas import behaviour and SCORM
  grade passback remain buyer-side steps, unverifiable from files alone.

## Artefacts

- `genuine/` + `genuine-zip/` — the two genuine Moodle exports tested.
- `run1_tgz_unmodified/`, `run2_zip_unmodified/` — pre-fix crash evidence
  (unmodified converter copies + inputs).
- `run3_zip_fixed/`, `run4_tgz_fixed/` — post-fix runs (converter copies,
  cartridges, `conversion-counts.json`).
- `validate_real.py`, `VALIDATION-REAL-OUTPUT.txt` — the validation suite
  and its passing output.
- `pre-fix-backup/` — pre-fix converter + sample outputs, for diffing.
- `sample-rerun-output.txt` — post-fix re-run of the original sample.
