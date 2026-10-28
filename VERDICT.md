# VERDICT — LMS Course Conversion (Moodle .mbz → Canvas .imscc)

**Internal document. Honest assessment, nothing inflated.**

## Headline verdict

**PERFORMABLE — with one disclosed gap.** The service as it would actually be sold —
a client supplies a Moodle backup file, we return a Canvas cartridge plus an
exception report — is **proven end-to-end at file level** on a deliberately gnarly
sample: the converter works, the counts reconcile exactly, and the validation suite
passes 13/13. The one thing not fully proven is the realism of our *hand-built
sample source*: a real Moodle 4.5 accepted and parsed it but did not fully
materialise it on restore (details below). That gap affects how perfectly the sample
imitates a real client file — it does not break the converter, whose input is the
same backup XML structure real Moodle exports produce.

## Exactly what is proven

1. **Course authoring → real backup structure.** We can generate a Moodle 4.5-format
   backup archive from structured source data: correct archive layout, hashed file
   storage in `files/`, per-activity XML, question bank, gradebook, rubric,
   availability (restrict-access) JSON, SCORM resource. (Scripts: `course_data.py`,
   `gen_mbz.py`.)
2. **Conversion.** `convert_mbz_to_imscc.py` converts that backup into a
   standards-shaped IMS Common Cartridge: 4 sections, 13 activity resources,
   4 QTI assessments (3 quizzes + question bank), 63/63 questions by type,
   197/197 feedback items, 224/224 response options, quiz membership exact (10/10 ×3).
3. **Byte-identical file transfer.** All 6 unique files (3 images, PDF, text file,
   SCORM zip) arrive SHA-1-identical, including images referenced from *inside*
   questions — verified per question (MC08, MC09, MC17), the failure mode buyers
   check first (per the Gemini cross-check).
4. **Honest exception handling.** The 3 calculated questions ship as clearly labelled
   placeholders (never force-converted); rubric, restrict-access rules, gradebook
   weighting, completion flags and SCORM passback are all named in a
   Pre-Migration Exception Report with the fallback taken (10 items).
5. **Independent validation.** `validate.py` re-derives every number from the two
   archives themselves (not from the converter's claims): XML well-formedness
   (77 + 5 + nested SCORM manifest), manifest reference resolution (21 hrefs),
   hash reconciliation, count reconciliation. **ALL CHECKS PASSED**
   (`VALIDATION-OUTPUT.txt`).
6. **Real-Moodle contact.** Moodle 4.5.15+ was installed locally (PHP 8.3 +
   MariaDB 10.11). Control backups from Moodle itself restore perfectly on it.
   Our backup's restore *completes*, the course and its 4 sections are created,
   and the restore's working tables provably load all 63 questions + category —
   i.e., a real Moodle parses our file deeply and correctly.

## What is NOT proven (do not claim otherwise)

1. **Full live-Moodle round-trip of our hand-built backup.** The restore's final
   creation phase produced 0 course modules / 0 questions in the database despite
   successful loading. Root cause not isolated within the timebox (full record:
   `MOODLE-RESTORE-LOG.md`). Consequences, stated plainly:
   - Our sample source is a *very close* but not *perfect* imitation of a real
     Moodle export. A focused follow-up session diffing against a real backup
     would likely close it, but that has not been done.
   - This does **not** undermine the converter: real client files are genuine
     Moodle exports (the control backups prove what those look like), and the
     converter consumes the documented backup XML, not restore behaviour.
   - It **does** mean: if a future client workflow required *us* to restore a
     backup into a live Moodle as part of the job, that step is unproven today.
2. **In-Canvas import behaviour.** No Canvas instance was available. The cartridge
   is standards-shaped and machine-validated, but Canvas's own link validator and
   a student-view SCORM test remain buyer-side steps (stated in the report).
3. **SCORM grade passback.** Cannot be verified from files alone — disclosed in the
   exception report, never claimed.
4. **Coverage beyond the sample.** Only the 7 question types and 5 activity types
   in the sample are proven. Real courses may contain other activity modules
   (forum, lesson, book, workshop, H5P…), other question behaviours, group/grouping
   restrictions, competency frameworks, multilingual content filters, and much
   larger banks. Each new construct is new converter work until proven otherwise.
5. **Other Moodle versions / other targets.** The sample targets the Moodle 4.5
   backup format and Canvas-flavoured IMS CC + QTI. Blackboard, D2L, Schoology or
   Moodle 3.x/4.0-era variants are plausible extensions, not proven capabilities.

## First real engagement — residual risks and mitigations

- **Risk:** a client's real backup contains a construct the converter mishandles
  silently. **Mitigation:** the validation script pattern (independent recount from
  the archives) must be run on every engagement; anything unreconciled goes to the
  exception report, never under the carpet. Start with a **single-course paid
  pilot** before any bulk commitment.
- **Risk:** buyer expects in-Canvas perfection from files alone. **Mitigation:**
  the report's verification-notes section sets the expectation up front (link
  validator + student-view SCORM check are theirs), which is also how professional
  migration firms frame it.
- **Risk:** scope creep into live-platform work (restoring, importing, fixing in
  their LMS). **Mitigation:** sell file-in/file-out only — which matches the
  no-platform-access positioning of the niche.
- **Pricing note:** nothing in this sample validates what buyers will pay; the
  price evidence lives in the research report, not here.

## Bottom line for the go/no-go decision

The deliverable pipeline (parse → convert → labelled exceptions → independent
validation → report) is real, working, and re-runnable today. Sell it as a
file-conversion service with a pilot-first engagement. Do not claim live-Moodle
restore or in-Canvas verification as in-house-proven steps.


---

## Addendum — 2026-10-24: real-export test (gap narrowed to closure for client files)

The gap disclosed above ("our sample source is a very close but not perfect
imitation of a real Moodle export; the converter is untested on genuine
exports") has now been tested directly. Full record:
`real-export-test/REAL-EXPORT-TEST.md`.

- A **genuine Moodle 4.5.15+ export** (CLI backup of the restored fixture
  course) was run through the converter. **Unmodified, it failed completely**:
  tar.gz container (Moodle's default) → `BadZipFile`; ZIP variant → crash in
  question loading (4.x bank-entry layout + multiple categories).
- **Ten disclosed, generalising fixes (F1–F10)** were applied to
  `convert_mbz_to_imscc.py`: container sniffing, `$@NULL@$` handling, 4.x
  question-bank layout, all three quiz slot forms (incl. random/filter set
  references, disclosed not faked), section directory/title handling,
  file-derived gradebook/completion exception text (the old text was
  hardcoded — and did not even match the sample file's own gradebook),
  shortname-derived manifest ids, and labelled-placeholder fallbacks for
  exotic question types and unhandled activity modules.
- After fixes: **both genuine containers convert end-to-end** to
  member-identical cartridges; an independent 26-check validation
  (`real-export-test/validate_real.py`) passes in full; the original sample
  re-run shows **zero count drift** and its 13/13 validation still passes.
- **Updated position:** the converter is now proven against real Moodle
  output — the input every client job actually starts from. What remains
  open is narrower: genuine-file coverage of activity/question types beyond
  quiz+truefalse (still proven on the hand-built sample only), fixed-slot
  references and multi-version entries (implemented, not exercised on a
  genuine file), the hand-built backup's live-restore quirk (moot for
  file-in/file-out work), and the buyer-side in-Canvas checks listed above.
