# Milestone 11: full-stack integration

## Local services and configuration

The application uses the existing PostgreSQL container, FastAPI services and
Next.js frontend. No authentication or public deployment was introduced. Groq
credentials stay in the backend's existing environment; there is no browser-side
provider integration.

From the repository root:

```powershell
docker compose up -d db
docker compose ps
```

The existing container exposes PostgreSQL only on `127.0.0.1:5433`. Root `.env`
contains the existing database configuration and backend Groq key. Never copy
that file into `frontend/`. The backend settings already read the root and backend
environment files. This validation reused them without printing their contents.

Backend terminal, from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If using the already downloaded embedding model in this repository, these
optional settings select the verified local cache and prevent metadata downloads:

```powershell
$env:HF_HOME = Join-Path (Get-Location) '.cache\huggingface'
$env:HF_HUB_OFFLINE = '1'
```

Do not enable offline mode before the initial model download on a fresh machine.

Frontend terminal, from `frontend/`:

```powershell
npm.cmd ci
if (!(Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Use `npm` instead of `npm.cmd` on other platforms. In `.env.local`, set only
`FASTAPI_BASE_URL=http://127.0.0.1:8000`. Never add Groq or PostgreSQL secrets.
The browser calls same-origin `/api/v1/*`; Next.js rewrites to the configured
FastAPI origin. Restart Next.js after changing configuration; rebuild when
using a production server. Direct `NEXT_PUBLIC_API_BASE_URL` access is optional
and requires explicit backend CORS configuration; the tested default rewrite
mode needs no CORS change. No second application backend was added.

Validation used isolated loopback ports **8011 (FastAPI)** and **3111 (Next.js)**
to avoid interfering with existing services. The build and frontend server both
received `FASTAPI_BASE_URL=http://127.0.0.1:8011`. Deterministic browser tests use
their own production server on 3100.

## Database and provider preflight

Docker reported the existing database container healthy. Read-only SQL verified
PostgreSQL 17.11, pgvector 0.8.7, `vector(384)`, and:

| Indexed document | PDF pages | Chunks | Classification |
|---|---:|---:|---|
| `2021-National-Cyber-Security-Policy-Final.pdf` | 22 | 52 | National policy |
| `NIST.CSWP.29.pdf` | 32 | 93 | Framework guidance |
| `CyberSage_Security_Incident_Casebook_RAG_v2.pdf` | 21 | 61 | Synthetic examples |

All three were `indexed`, totaling 75 pages and 206 chunks. No invalid dimensions,
orphan chunks or out-of-range pages were found. The catalog matches this corpus;
it remains explicitly labeled a snapshot because no inventory endpoint exists.
No reingestion, document deletion or schema change was performed.

The project uses explicit SQL migrations, not a `schema_migrations` ledger.
The existing `conversations`, `conversation_turns` and `conversation_messages`
tables were present. Regression tests exercised the migration constraints in
temporary PostgreSQL tables. Do not rerun migration 002 against an already
initialized database. For a fresh database only, follow the explicit migration
commands in README before ingestion. Existing source tables/data were preserved.

The Groq SDK's account model list confirmed that configured
`openai/gpt-oss-120b` is available. Only key presence was reported; its value
was never printed or copied into frontend configuration.

## Integration changes and verified contracts

The served FastAPI OpenAPI document and Python implementations were inspected.
The actual agent request requires `message`; optional fields are `likelihood`,
`impact`, `top_k`, `conversation_id` and `request_id`. Responses preserve:

- `capability`, `status`, nullable `answer`/`assessment`/`error`/`model`.
- Database-derived `citations` with title/filename, physical PDF page, chunk and
  evidence IDs, quote and source classification.
- Retrieved/selected evidence counts, abstention reason, conversation/request
  IDs, resolved message and `context_used`.

The history endpoint is
`GET /api/v1/conversations/{id}/messages?limit=10&before_turn=…`, returning
`messages`, `has_more` and `next_before_turn`. There is no list-all-conversations
endpoint. Health is `/api/v1/health`; ask/search remain `/api/v1/rag/ask` and
`/api/v1/retrieval/search`.

Frontend runtime validators now reject malformed agent, risk, history and health
JSON before display. They check fields, status values, citation structure,
pagination, risk product/category consistency and citation-free abstentions/risk
responses. These are structural checks, not evidence entailment checks. Backend
citation validation remains authoritative and unchanged. The unused direct
ask/search client methods retain their compile-time interfaces; live browser
flows use the validated agent endpoint.

New successful conversations replace the assistant URL with their actual ID,
so refresh restores server history. Follow-ups send that same ID. A failed
request retries the original payload and request UUID; simultaneous sends are
locked. Generated content still renders without raw HTML, actionable generated
links or tracking images. Citations expand locally to show returned evidence;
they do not navigate to invented PDF URLs. Synthetic citations remain labeled.

Risk Analyzer selectors/matrix remain a **local preview**. The explicit confirm
action submits `message: "Calculate risk"` plus integer ratings and a request
UUID to the agent. A separate result shows only the returned server assessment.
Changed inputs do not relabel an old confirmed result as current. Failed
confirmations preserve the retry payload. No LLM calculates scores; risk
responses contain no PDF citations.

## Actual failure investigated

The first live NIST browser request received a non-JSON “Internal Server Error”
response after roughly 32 seconds. Next.js logged `ECONNRESET` / `socket hang up`.
Its installed rewrite implementation defaults to a 30-second proxy timeout,
which can expire during cold model initialization plus grounded generation.
The original attempt was retained separately in ignored local evidence.

The rewrite timeout is now explicitly 125 seconds, slightly beyond the existing
120-second client abort. Both are bounded. SDK provider timeouts remain unchanged,
and retries preserve request IDs to handle a response lost after server commit.
The validation services were restarted before rerunning. A one-time thread
diagnostic showed an idle event loop before the rerun, not an observed backend
deadlock. No RAG or citation rule was relaxed. Final live results below are from
the separate post-fix run; the initial failed attempt is not counted as passed.

## Browser tests and live evidence

Deterministic browser tests explicitly intercept API requests and are separate
from `live/fullstack.spec.ts`, which uses real services with **no route mocks**.
The live script spaces Groq questions 65 seconds apart. Full responses and access
IDs are retained only under ignored `frontend/.cache/milestone11/`; sanitized
public results and citation audits accompany this report.

### Actual live outcomes

The final post-fix run completed in 2.8 minutes, crossing 13–14 November 2026
in Asia/Karachi. Machine-readable timestamps are UTC.
See [sanitized live responses and audits](milestone11-live-results.json).

| Scenario | Actual outcome |
|---|---|
| A — NIST incident response | HTTP 200, `answered`, 24.168 seconds including cold initialization; two citations: NIST PDF p. 27/chunk 76 and p. 20/chunk 57 |
| B — “What about recovery?” | HTTP 200, `answered`, 4.974 seconds; same conversation, `context_used: true`, resolved to “What does NIST CSF 2.0 say about recovery?”; five citations: four excerpts from PDF p. 28/chunk 79, one from p. 27/chunk 78 |
| C — likelihood 4, impact 5 | Actual agent response `assessed`, score **20**, category **Critical**, no model/citations; displayed in the separate server-confirmed card |
| D — Mars policy in 2050 | HTTP 200, `insufficient_evidence`, 1.436 seconds, zero citations; a different new conversation |
| E — refresh/reopen | Browser refresh restored both assistant turns; direct history read returned HTTP 200 and four messages with both original user questions |
| Invalid risk input | Actual request with likelihood 0 returned HTTP 422 |
| Mobile | Saved real conversation restored at 390px; no horizontal overflow |
| Browser script errors | Zero `pageerror` events in the final live run |
| Read-only UI review | Additional real-service check of five pages plus restored history at 1440px/390px: zero console or page errors, no horizontal overflow, zero additional Groq calls |

A's source quote covers response management, coordinated plan execution,
triage/validation, prioritization, escalation, recovery criteria and incident
analysis. The additional p. 20 framework category listing is genuine but less
detailed. B's actual excerpts cover selecting/prioritizing recovery actions,
verifying backup integrity before restoration, considering critical mission
functions, validating restored assets and normal operation, and the RECOVER
function definition. These excerpts are relevant and supported; they are not a
claim of exhaustive coverage of the whole framework.

Both turns made real agent calls. The resolved follow-up and retrieved/selected
counts are recorded. Existing orchestration invokes RAG with that resolved
question and performs fresh retrieval; prior assistant content is not supplied
as source evidence. Selected prompt text was not captured or published.

Independent checks against PostgreSQL and actual PDF pages passed for **all
seven returned citations**, including titles/filenames, pages, chunk/evidence IDs
and exact whitespace-normalized quotes. The first local audit incorrectly read
Node's UTF-8 JSON with Windows' default encoding, corrupting a bullet character;
specifying UTF-8 corrected the audit. No production quote, citation normalizer
or Milestone 9 artifact was changed. Quote origin is distinct from factual
entailment/completeness; relevance was also inspected against the question.

All configured credentials were searched in the built browser output: **zero
matches** across 34 static files. The public result export also masks access IDs.
The known configured model was confirmed through Groq's real account model list.

### Genuine screenshots

The following actual local image files were captured from the real browser,
without mocked health, answers or assessments:

- `frontend/.cache/milestone11/overview.png`
- `frontend/.cache/milestone11/assistant-citations.png`
- `frontend/.cache/milestone11/risk-confirmed.png`
- `frontend/.cache/milestone11/memory.png`
- `frontend/.cache/milestone11/memory-mobile.png`

The memory screenshots were recaptured from the same persisted conversation,
scrolling to the follow-up and contextual resolution without another generation
call. The risk screenshot was refreshed with another actual server assessment
after returning scroll/focus to the page top; that response is retained in the
public JSON. Citation cards expand to display the real source quote; they are not PDF
download links. Screenshots were visually inspected. They are ignored generated
evidence, not committed files; preserve them locally for the assignment.

### Regression checks

- **332 backend tests passed**, with real PostgreSQL integration enabled.
- **41 frontend unit/component tests passed**, including response-contract
  rejection, risk submission/retry and the existing Markdown safety tests.
- **8 deterministic Chromium tests passed** with explicitly mocked APIs:
  navigation/accessibility, mobile layout, submit/retry/copy/citations, history
  pagination, follow-up/refresh/deduplication, server risk preview distinction,
  invalid input and backend-unavailable behavior.
- **1 separate live Chromium test passed**, covering A–E above with real services.
- **1 additional read-only live Chromium review passed** for desktop/mobile
  console errors and layout, without additional Groq calls.
- Strict TypeScript, zero-warning ESLint, production build, dependency checks,
  whitespace and staged secret review were executed before the commit.
- Backend `pip check`: no broken requirements. No Python dependency/schema
  changes were required. The corpus remained three indexed documents/206 chunks.

The mocked tests prove deterministic UI behavior, not provider relevance. The
live result proves these specific scenarios, not every future Groq response.
Existing rate-limit/provider failure handling remains in effect.

## Reproducing validation

From `frontend/`:

```powershell
npm.cmd run build
npm.cmd run typecheck
npm.cmd run lint
npm.cmd test
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.cache\playwright'
npm.cmd exec -- playwright install chromium
npm.cmd run test:e2e
# Start real FastAPI and a production frontend separately, then:
$env:LIVE_FRONTEND_URL = 'http://127.0.0.1:3111'
npm.cmd exec -- playwright test --config playwright.live.config.ts
npm.cmd audit
```

The live frontend must be built/started with its actual `FASTAPI_BASE_URL`.
Live runs are opt-in, consume provider quota and create ordinary conversations.
Previous private run JSON is archived rather than overwritten. Screenshot files
are generated locally and are not committed. Playwright tracing is disabled for
the live run to avoid publishing history-access IDs. Windows sandbox restrictions
required approved process/network access for Docker, Groq and browser cleanup.

Backend, from `backend/`:

```powershell
$env:CYBERSAGE_TEST_POSTGRES = '1'
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider --basetemp=.cache/pytest-milestone11
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe verify_fullstack_manual.py
```

`verify_fullstack_manual.py` independently audits the private live JSON against
database metadata and source PDFs, scans browser bundles for configured secrets,
and writes the sanitized public JSON. It makes no generation calls and explicitly
reads UTF-8. Run it after a live test and production build. Private conversation
and request IDs remain only in the ignored local capture.

## Privacy and remaining limits

Authentication remains out of scope: knowing a conversation UUID grants history
access. Recent shortcuts retain only IDs, initial titles and timestamps in this
browser, never enumerate server conversations, and do not delete server history
when cleared. Do not use sensitive questions on shared machines. This validation
was loopback-only; there was no public deployment.

Citation provenance and exact quotes do not prove answer completeness. Existing
Milestone 9 failures remain unchanged. The permissive retrieval threshold does
not guarantee relevance. Concurrent turns can return 409; the UI uses a bounded
single request and safe retry. The opt-in live test does not replace broad model
evaluation. Browser coverage is Chromium; Firefox/WebKit and manual screen-reader
audits remain future validation work. The proxy-timeout setting is an experimental
Next.js option and should be revisited during framework upgrades.
