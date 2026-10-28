# Live-Moodle Restore Attempt — Log (bonus validation, timeboxed)

**Environment built from scratch on this machine:** PHP 8.3.6 + MariaDB 10.11.14,
Moodle **4.5.15+ (Build: 20261021)** extracted to `~/moodle`, dataroot `~/moodledata`,
CLI install completed successfully.

## Controls (install + container proven good)
- Moodle's own shipped fixture backup `mod/quiz/tests/fixtures/moodle_311_quiz.mbz`
  restored fully: 1 course module, 1 quiz, 2 questions.
- The same fixture repacked as a ZIP (the container format our generator produces)
  also restored fully — so the ZIP `.mbz` container is not the problem.
- A backup produced by this Moodle itself (of the fixture course) was used as the
  structural reference for real 4.5 backup files.

## Our sample backup — what happened
Restoring `Sample-Course-Moodle-Backup.mbz` via `admin/cli/restore_backup.php`:

1. The restore **runs to completion** (controller status FINISHED_OK) and creates the
   course with the correct full name/shortname and its **4 named sections**.
2. Verified directly in the restore temp-ids table after the root task: the backup is
   parsed deeply — **all 63 questions and the question category load successfully**
   (`question: 63`, `question_category: 1`, `question_category_created: 1`,
   `question_categoryref: 1`, `fileref: 5`).
3. However, the restore finishes with **0 course modules and 0 questions** in the
   database: the per-item *creation* phase (activity structure steps and question
   creation) silently produces nothing for our file, while the identical phase works
   for Moodle-produced backups.

## Fixes applied during the attempt (each found from Moodle source/debug harness)
- `moodle_backup.xml`: `<details>` rewritten to the real nested shape
  (`<detail backupid="...">` with type/format/mode); settings rewritten as real
  `<setting>` elements at root (level "course"), per-section and per-activity.
- Backup version fields set to a real release (2024100715 / 4.5.3) — a development
  version stamp is rejected by restore prechecks.
- Added files a real backup always carries: root `roles.xml` (role definitions),
  `groups.xml`, `scales.xml`, `outcomes.xml`; `course/roles.xml`,
  `course/competencies.xml`, `course/completiondefaults.xml`; per-activity
  `roles.xml` (13 files).

## Outcome
**Partial.** The backup is accepted, parsed and loaded by a real Moodle 4.5, but the
final creation phase does not materialise activities/questions from it. The exact
remaining root cause was **not isolated within the timebox** despite source-level
investigation (plan construction, task settings, inforef references and parser paths
were all verified correct). Recorded honestly as an open item — see VERDICT.md for
what this does and does not affect.
