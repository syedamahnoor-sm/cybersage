# Milestone 12 submission verification

Prepared on **November 14, 2026** (Asia/Karachi), from implementation commit
`60d443dd8d4dfb1c87a97dc15397b3a0094d02bd`. This log separates newly executed
checks from historical evaluation/integration evidence.

## Newly executed checks

| Check | Actual observation |
|---|---|
| Backend pytest with PostgreSQL enabled | **332 passed**, 14.03 seconds |
| Python dependency check | `pip check`: no broken requirements |
| Frontend Vitest | **41 passed**, five test files, 15.36 seconds |
| Production build | Passed; five application pages, not-found route and favicon generated |
| Strict TypeScript | `tsc --noEmit` passed |
| ESLint | Passed with zero warnings |
| Functional browser tests | **7 passed**, 24.4 seconds; one screenshot-generation test deliberately excluded |
| npm audit / installed dependencies | Zero vulnerabilities; `npm ls --depth=0` completed successfully |
| Documentation links / staged secrets / whitespace | Passed: 72 local links, 14 staged documentation/evidence files reviewed, no whitespace errors |

Commands actually used, from `backend/`:

```powershell
$env:CYBERSAGE_TEST_POSTGRES = '1'
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider --basetemp=.cache/pytest-milestone12
.\.venv\Scripts\python.exe -m pip check
```

From `frontend/`:

```powershell
npm.cmd run build
npm.cmd run typecheck
npm.cmd run lint
npm.cmd test
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.cache\playwright'
npm.cmd run test:e2e -- --grep-invert "capture actual local"
npm.cmd audit --fetch-retries=0 --fetch-timeout=20000
npm.cmd ls --depth=0
```

The screenshot-generation browser test is deliberately excluded: submission
instructions require preservation of existing evidence rather than regeneration.
The other tests use explicit mocked APIs, not live Groq. No new live generation
run or replacement ten-question evaluation was performed in this milestone.

## Historical evidence independently inspected

The Milestone 9 dataset/reviews/results were parsed together. They confirm:
8 answerable + 2 unanswerable; 5 full answer passes + 1 partial + 2 incorrect
abstentions + 2 correct abstentions; 15/21 criteria (71.4%); 12/12 citation
records verified; zero unsupported answers observed under the documented review
scope. Ground-truth excerpts and source hashes were reverified against the
actual PDFs. The seven review rows labeled “pass” include correct abstentions.

Milestone 11's [sanitized live evidence](milestone11-live-results.json) was read
and cross-checked with its [integration report](milestone11-integration.md).
It records the completed real Groq scenario, seven valid citation audits,
four-message persistence, server-confirmed 20/Critical, correct Mars abstention,
and a separate completed read-only UI review. Its eight mocked browser tests
and two live checks are **historical results**, not newly rerun submission tests.

## Evidence preservation

All five original PNGs were opened for visual review. They show ordinary demo
questions and source evidence, with no visible keys, passwords or conversation
access IDs. Each was copied unchanged from `frontend/.cache/milestone11/` to
`docs/submission-evidence/`; [manifest.json](submission-evidence/manifest.json)
records original paths, dimensions, byte sizes and SHA-256 hashes. No cropping,
retouching, recomposition or regenerated screenshots were used.

Before running builds, all existing evaluation files and the original generated
declaration were snapshotted privately for end-of-run comparison. Original
Milestone 9 observations were checked by hash and by Git diff against original
evaluation commit `0d301dc`; both checks found no changes.
The pre-existing `next-env.d.ts` change consists only of `.next/dev/types/`
imports; build-generated production imports must not silently replace it.

## Completion record

Local documentation checks found **72 valid relative Markdown/image links**
across **16 Markdown files**, with no unresolved file paths. Five external
Markdown links were excluded from that local check; assessor access remains a
manual check. All five source/destination PNGs are byte-identical. All 15
snapshotted evaluation/report files are unchanged. The generated declaration
was restored to its exact original bytes and remains unstaged.

Staged review inspected **14 documentation/evidence files**, finding no
configured credentials, live conversation/request access IDs, or PNG text/EXIF
metadata. `git diff --cached --check` passed. A remote fetch confirmed `main`
aligned with `origin/main` before the submission commit. No application or
evaluation source files are staged; the original declaration change is excluded.

Student name replacement, human rehearsal, assessor access,
attachment verification and email sending remain manual actions in the
[submission checklist](submission-checklist.md).
