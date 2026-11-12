# Milestone 6 validation

Latest status: **Milestone 6.1 live validation completed** with the configured
Groq account and `openai/gpt-oss-120b`. Three source-backed questions were answered;
the Mars question correctly abstained. Details and initial failures are below.

## Implemented behavior

Provider-neutral orchestration reuses existing semantic retrieval, selects a
bounded set of whole evidence passages, and asks the configured Groq text model
to select exact supporting excerpts. A local gate validates schema, selected
evidence IDs, and whitespace-normalized quote membership. A second provider call
reviews relevance and contextual support. The server renders only validated
quotes and database-derived citation metadata; it never returns unrestricted
model-generated prose or model-generated page/title references.

Unknown IDs, modified quotes, irrelevant evidence verdicts, malformed/truncated
outputs, exhausted context budgets, and model-declared insufficiency cause
explicit abstention with no citations. Empty retrieval and quarantined/unusable
contexts avoid provider calls altogether. Operational provider failures remain
503/504 errors rather than being mislabeled as insufficient evidence.

## Executed checks

- Full suite with `CYBERSAGE_TEST_POSTGRES=1`: **163 passed**, including 12 real
  PostgreSQL tests. The original ingestion and retrieval tests still pass.
- Ordinary offline suite: **151 passed, 12 PostgreSQL tests skipped** as intended.
- Tests mock all external LLM inference, model validation, timeouts, rate limits,
  connection failures, unavailable models, and missing credentials. No actual API
  key is present in fixtures or test output.
- Real PostgreSQL integration runs retrieval, RAG orchestration, and the endpoint
  together with only model inference mocked. Citations retained the stored
  document/chunk IDs, physical PDF page 27, and chunk index. No source records
  were changed by the tests (temporary tables and rollback).
- Citation tests reject nonexistent or unselected IDs, altered/invented claims,
  irrelevant excerpts even when ID/quote checks pass, and reviewer-ID mismatches.
  Retrieved but uncited chunks do not become citations. Synthetic source excerpts
  are explicitly qualified as examples, not real events.
- Malicious source tests cover obvious instruction quarantine, role-like text
  remaining in untrusted JSON rather than system instructions, and rejection of
  injected free-form answer fields. These tests do **not** prove real-model prompt
  injection resistance.
- Budget tests cover serialized evidence length, deduplication, stable chunk-based
  IDs, retrieval-count caps, and pre-call whole-prompt limits. The provider adapter
  passes configured temperature, timeout, maximum completion tokens, JSON mode,
  and zero SDK retries; validated model/client reuse and cleanup are tested.
- Actual FastAPI requests with the real indexed corpus and missing credentials
  returned **503** with only `Answer generation is temporarily unavailable.`
  A whitespace question returned **422**. A separate real-retrieval check using
  cutoff 1.0 produced no evidence and returned **200**,
  `status=insufficient_evidence`, empty citations, and `model=null`, without Groq.
  The strict cutoff was a test-only dependency override, not a settings change.
- Ingestion rerun: **3 skipped, 0 inserted chunks, 0 failures**. Verification
  retained **3 indexed documents / 206 chunks**, with zero invalid dimensions,
  norms, page references, orphan chunks, or duplicate chunk indices.
- `pip check` passed. Git whitespace and staged secret/file checks are required
  before the milestone commit.

## Initial Milestone 6 live status (before Milestone 6.1)

At the original Milestone 6 run, no `GROQ_API_KEY` was found in process or configured root/backend environment
files. The explicit `test_rag_manual.py` check printed
`live_llm_status=skipped_missing_credentials`. **No live Groq answer, unanswerable
question result, rate-limit behavior, latency, or account-model availability is
claimed as validated.**

The configurable default `openai/gpt-oss-120b` was selected using Groq's current
[supported model documentation](https://console.groq.com/docs/models) and
[deprecation notices](https://console.groq.com/docs/deprecations). The adapter
validates the configured model through Groq's models endpoint on first use with
credentials. Public documentation is not proof of availability for an account.

The original manual script covered the three corpus questions and an unanswerable
malware-hash question. Milestone 6.1 updates it to the four requested questions,
including the Mars-policy question, with rate-limit pacing and explicit synthetic
source labeling checks.

## Milestone 6.1 live validation

The configured key is now present; only its presence was inspected or reported.
Groq's authenticated model list contains active `openai/gpt-oss-120b`, and live
completions confirmed account access. Neither credentials nor raw SDK exception
bodies were printed or recorded. Local diagnostic reports were scrubbed and kept
under ignored `backend/.cache/`; raw PDFs, model files, and `.env` remain excluded.

### Failures investigated and minimal fixes

- The original `models.retrieve("openai/gpt-oss-120b")` lookup returned HTTP 404
  although the same ID was active in `models.list()`. The adapter now validates
  against the account's model list and still rejects missing/inactive IDs. It does
  not silently switch models. Tests ensure the namespaced model uses the list
  route, never the failing single-model route.
- The first unpaced run answered NIST and Pakistan questions, then hit Groq rate
  limits on ransomware and Mars (HTTP 503 with safe messages). Those two requests
  produced no answer and do not count as an insufficient-evidence success.
  Validation was rerun with 65-second spacing between questions. API retry and
  timeout policy was left unchanged.
- The initial NIST answer quoted a useful RESPOND passage but copied its cut-off
  trailing phrase ending in `the records’`. It matched the source exactly, yet
  was visibly incomplete. Selection instructions now ask for complete sentences
  or list items, excluding cut-off tails. A conservative local check rejects
  quotes ending on a dangling possessive, dash, comma, or colon. A regression test
  rejects this case even when its quote is verbatim. ID, quote membership, and
  relevance gates remain intact; citation integrity was not relaxed.

### Automated regression validation

Affected provider/RAG tests: **47 passed**. Full suite with real PostgreSQL:
**165 passed**, including the two new regressions and the existing 12 PostgreSQL
tests. `pip check` passed. The database still contains 3 indexed documents and
206 chunks, with no invalid dimensions, norms, page references, or orphan chunks.

### Final paced live run: actual results

All requests used the actual `POST /api/v1/rag/ask` application through FastAPI's
TestClient, real MiniLM retrieval, PostgreSQL/pgvector, and real Groq selection
and review calls. No retrieval, provider, model output, or database dependency was
mocked in this run. Request `top_k` was 5 and the configured retrieval cutoff was
0.2. Each question retrieved/selected five chunks. Questions were spaced 65
seconds apart; the per-request times below exclude that intentional spacing.

| Question | HTTP | Status | Time | Citation records |
|---|---:|---|---:|---:|
| How does NIST CSF 2.0 address incident response? | 200 | answered | 22.19 s | 3 |
| What does Pakistan's National Cyber Security Policy say about critical infrastructure? | 200 | answered | 2.86 s | 1 |
| Describe the ransomware incident in the CyberSage casebook. | 200 | answered | 4.17 s | 2 |
| What is the cybersecurity policy of Mars in 2050? | 200 | insufficient_evidence | 1.01 s | 0 |

The first timing includes embedding-model startup; these single observations are
not a latency benchmark. The run made seven completion calls (selection + review
for each answered question, selection-only for Mars), plus model-list validation.
No rate-limit, timeout, invalid-ID, quote-membership, or review failure occurred in
this final run. Three answerable questions were answered; no excessive abstention
was observed in this small sample. This is not a representative evaluation set.

#### NIST: actual returned excerpts

All three were rendered with `Framework guidance:` and
`[NIST.CSWP.29.pdf, p. 27]`:

> The incident response plan is executed in coordination with relevant third parties once an incident is declared

> Incident reports are triaged and validated

> Incidents are categorized and prioritized

Citation metadata: document `7bc85d48-0606-4e6b-aa7e-f453e59cca0a`, chunk
`45eebff5-cd2b-40b6-879d-f1161f0d7452`, chunk index **76**, evidence ID
`E_45eebff5cd2b40b6879df1161f0d7452`. The physical PDF page is **27** (printed page
22). Manual review: directly relevant incident-management guidance; it is a
partial extract, not a complete account of all CSF response/recovery categories.

#### Pakistan policy: actual returned excerpt

Rendered with `Policy source:` and
`[2021-National-Cyber-Security-Policy-Final.pdf, p. 11]`:

> Will regard a cyber-attack on Pakistan CI/ CII as an act of aggression against national sovereignty and will defend itself with appropriate response measures.

Citation metadata: document `0da5f587-861b-47b4-a653-2a301888ef60`, chunk
`25a57286-33a0-4d78-928c-5daeaaf524c9`, chunk index **24**, evidence ID
`E_25a5728633a04d78928c5daeaaf524c9`. The physical PDF page is **11** (printed page
8). Manual review: directly addresses the policy's treatment of CI/CII attacks,
without inventing legal obligations or claiming to enumerate every CI measure.

#### Casebook: actual returned excerpts

Both were rendered with **`Synthetic incident example (not a real event):`** and
`[CyberSage_Security_Incident_Casebook_RAG_v2.pdf, p. 3]`:

> Ransomware containment in a file services segment Incident reference CS-INC-002 Recorded date 21 February 2026 Operating location Islamabad, Pakistan Organization sector Professional services Primary affected service Windows file server and backup infrastructure Asset reference PK-ISL-002 Initial triage priority Critical Case status Closed - monitoring and follow-up controls in progress Incident overview The professional services organization operating in Islamabad recorded a security event affecting its windows file server and backup infrastructure.

> Detection and observed evidence Endpoint telemetry detected rapid file renaming and an unsigned encryption process on a shared drive.

Citation metadata: document `114762b2-d981-4d8a-b3fe-746d27ead5fe`, chunk
`415d0d6b-f150-45d0-838d-e4645ef3586f`, chunk index **4**, evidence ID
`E_415d0d6bf15045d0838de4645ef3586f`. Manual review: relevant case identity,
affected infrastructure, and detection evidence. Fictional/synthetic status was
explicit in both answer sections. The answer is verbose and does not provide a
complete chronology or detailed containment actions; none were inferred.

#### Mars: actual returned answer

> The available source evidence is insufficient to answer this question reliably.

Status `insufficient_evidence`; reason `model_abstained`; citations `[]`; model
`openai/gpt-oss-120b`. Five chunks passed retrieval's permissive cutoff, but the
selection model correctly found them insufficient. This validates the explicit
abstention path beyond empty retrieval; no Martian policy or citation was invented.

### Citation verification and remaining limits

All **six citation records**, covering **three distinct chunks**, passed checks
against database document/chunk UUIDs, filename/title, PDF page, chunk index,
stable evidence ID, and exact quote membership after whitespace normalization.
Each quote also matched text extracted from the original physical PDF page. The
stored titles remain null, so display labels use the exact filenames. No title,
page number, evidence ID, or quoted fact was invented in the returned answers.

The local gates and relevance model approved all final answers; manual inspection
also found them relevant and supported for the limited claims returned. This is
not proof of source truth, exhaustive coverage, or general factual entailment.
The same-model review remains fallible. The narrow punctuation-ending check can
reject legitimate excerpts and does not detect every incomplete sentence. Rate
limits remain an operational constraint; 65-second smoke-test spacing succeeded
here but is not a general quota guarantee. Credentials were never printed,
staged, or committed. Live validation is no longer blocked by missing credentials.

## Limits of the grounding contract

Exact ID/quote checks establish provenance of returned excerpts, not factual
entailment, source truth, or completeness. The second relevance check uses the
same LLM and can share its failure modes. Source-type classification and the
injection scanner are conservative heuristics; neither authenticates a document
nor detects every attack. Evidence may omit conditions outside the selected
passage. Character budgets are not exact token counts. Provider timeouts apply
per request, not to the entire RAG request. The extractive mode can abstain more
often and provides less fluent synthesis than unrestricted prose generation.

No agents, risk scoring, conversation memory, authentication, frontend, or
deployment were added.
