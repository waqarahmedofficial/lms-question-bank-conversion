# LMS Question-Bank Conversion — Moodle .mbz → Canvas .imscc

**File-in, file-out course conversion: send a Moodle backup, receive a validated Canvas cartridge plus an honest exception report.**

Built by **Waqar Ahmed**, spreadsheet & data specialist (7+ years: data cleaning, conversion, validation and reporting).

## Who this is for

Training providers, course creators and LMS migration projects moving content from Moodle to Canvas — especially question banks, where silent question loss or broken images are the failures that hurt most. No platform access is needed or requested: the service works entirely on files.

## What the proof in this repo shows

A deliberately demanding sample course (63 questions across 7 question types, 3 quizzes + question bank, embedded images, PDF/text/SCORM files, rubric and access rules) was converted from a Moodle backup (`.mbz`) to an IMS Common Cartridge (`.imscc`), then verified by an **independent validator that re-derives every number from the two archives themselves** — not from the converter's claims.

| Measure | Result |
|---|---|
| Questions converted | **63/63** (multiple choice 25, true/false 10, short answer 8, matching 6, numerical 6, essay 5, calculated 3 as clearly labelled placeholders) |
| Feedback items | 197/197 |
| Response options | 224/224 |
| Files transferred | 6/6 **byte-identical** (SHA-1 verified — including images referenced from *inside* questions) |
| Sample validation suite | **13/13 checks PASS** (`VALIDATION-OUTPUT.txt`) |
| Genuine Moodle 4.5 export test | A real Moodle 4.5.15+ export converts end-to-end after 10 disclosed converter fixes; independent validation **26/26 PASS** (`real-export-test/`) |

**Honest caveats** (the same ones stated to clients, in full in `VERDICT.md`):
- The genuine Moodle 4.5 export used for the 26/26 test was thin (quiz + true/false questions); the remaining question types are proven on the hand-built sample, whose backup format a real Moodle parses deeply and correctly.
- The 3 calculated questions ship as **clearly labelled placeholders**, never force-converted; rubric, access rules, gradebook weighting and similar constructs are named in a Pre-Migration Exception Report with the fallback taken — nothing is silently dropped.
- Buyer-side steps remain buyer-side: Canvas's own import/link check and a student-view SCORM test happen in your Canvas instance.

Files: the converter (`convert_mbz_to_imscc.py`), the independent validator (`validate.py`), the sample source backup and converted cartridge, the conversion report, count reconciliations, and the full verdict with the real-export test record.

## What you receive on a real engagement

- The converted `.imscc` cartridge, ready to import into Canvas
- A Pre-Migration Exception Report: every construct that could not convert 1:1, named, with the fallback taken
- A count reconciliation: questions, options, feedback and files — source vs converted, independently recounted
- The validation output for your files

## How the work runs

1. **Pilot first** — one course converted end-to-end so you can verify the result in your own Canvas before any bulk commitment.
2. **Convert** — parse → convert → labelled exceptions, using the same pipeline proven here.
3. **Validate** — the independent recount runs on every engagement; anything unreconciled goes in the exception report.
4. **Deliver** — cartridge + exception report + validation output, in writing.

## Tools

Python · Moodle 4.5 backup format (XML) · IMS Common Cartridge · QTI

## About this sample

Proof of capability on a self-built sample course plus a genuine Moodle export fixture — no client course content is used or shown. What is proven and what is not is written down in `VERDICT.md`; please read it — that honesty is part of the service.

## Work with me

I take on freelance projects through Contra: **https://contra.com/mr_world_z7lsrx86**

Communication is **written-only** (chat/email) — clear briefs, documented handovers, no calls needed. Payment via Payoneer or bank transfer.
