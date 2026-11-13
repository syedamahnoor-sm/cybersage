# Milestone 9: RAG agent evaluation and failure analysis

Live evaluation performed on 13 November 2026 against the existing local API,
PostgreSQL corpus and Groq `openai/gpt-oss-120b`. The evaluation completed;
completion does **not** mean every answer passed. No production retrieval,
generation, citation, memory or risk-scoring code was changed.

## Artifacts and reproducibility

- [Dataset](../backend/evaluation/dataset.json): exactly ten questions, eight
  answerable and two unanswerable. Answerable distribution: three Pakistan policy,
  three NIST CSF 2.0, two synthetic casebook questions.
- [Machine-readable observations](../backend/evaluation/results/milestone9.json):
  full answers, statuses, citations, latency, diagnostic retrieval, source hashes,
  configuration, comparisons and metrics. The initial implementation commit is
  recorded. No failed answer was replaced with a later successful retry.
- [Source review](../backend/evaluation/reviews.json): grades and criterion-level
  judgments, bound to each recorded response by SHA-256.
- [Complete ten-question results](milestone9-results.md): table, actual answers,
  citations, expected criteria and review notes.
- [Separate risk and memory observations](../backend/evaluation/results/supplementary.json).

Ground truth was checked against all three actual PDFs before inference. All 21
criterion excerpts matched their physical PDF pages. Policy has 22 pages, NIST
32, and casebook 21 (75 total). Expected pages are PDF page numbers, not printed
body-page labels: NIST PDF p. 27, for example, is printed page 22. Source SHA-256
hashes are recorded; raw PDFs remain excluded from Git. No evaluation questions
were inserted into indexed documents. Corpus totals remained three indexed
documents and 206 chunks. New evaluation conversations are separate application
data, not extra source documents.

From `backend/`, with PostgreSQL, the cached embedding model and local environment
configured, start the existing API in one terminal:

```powershell
$env:HF_HOME = Join-Path (Get-Location) '.cache\huggingface'
$env:HF_HUB_OFFLINE = '1' # only when the model is already cached
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Run a new evaluation in another terminal:

```powershell
.\.venv\Scripts\python.exe -m evaluation --output evaluation/results/new-run.json
.\.venv\Scripts\python.exe -m evaluation.extra --output evaluation/results/new-supplementary.json
```

The default delay is 65 seconds between RAG questions. Risk requests make no LLM
calls; the memory demo waits 65 seconds before its first question and between its
two turns. A ten-question evaluation takes several minutes. Keep provider quotas
in mind; a delay cannot guarantee freedom from account-wide rate limits. No
automatic answer retry is used. `--resume` runs only unexecuted items and refuses
a changed dataset; it does not replace recorded failures. Choose a fresh filename
for a new experiment. Result files are checkpointed atomically after each item.

The runner calls the existing HTTP agent, never duplicates its orchestration.
Each question omits conversation ID, supplies a new request ID, and verifies a
different returned conversation plus `context_used: false`. Public artifacts mask
access IDs. A separate read-only retrieval API call records diagnostic evidence;
those passages are **not injected** into agent generation. They are not a trace
of the agent's selected prompt. The initial run was completed before later
checkpoint/error-reporting hardening; the production agent and its settings
remained unchanged throughout.

Missing credentials or HTTP/transport errors make the run incomplete, not a
successful abstention. The CLI reports incomplete runs with a nonzero exit code.
Exception types/safe HTTP statuses are recorded instead of internal exception
bodies. API keys, configured database passwords and private access IDs are
redacted; no environment files are copied.

## Grading rules and results

A manual review here means the implementation assistant compared the actual
answers, cited quotes and verified PDF criteria. It is not independent expert
grading and is not an LLM-as-judge benchmark.

| Measure | Rule | Actual result |
|---|---|---|
| Executed | Ten independent agent requests, excluding risk/memory checks | 10/10 |
| Answered | Successful `answered` status | 6 |
| Correct abstention | Unanswerable + `insufficient_evidence` + no citations | 2/2 |
| Incorrect abstention | Answerable + `insufficient_evidence` | 2/8 |
| Unsupported answers | Answered unanswerable question, or manually identified unsupported answer | 0 observed |
| Citation metadata validity | ID, document, filename/title, PDF page and chunk index match database | 12/12 |
| Quote provenance | Valid metadata + exact normalized quote in database chunk and raw PDF page | 12/12 |
| Citation source relevance | Citation filename equals expected source | 12/12 |
| Coverage | Expected atomic answer criteria actually addressed, including failures as zero | 15/21 (71.4%) |
| Average response latency | Wall time around agent HTTP call only | 2.631 seconds |
| Manual overall grade | Correct, complete, supported answer or correct abstention | 7 pass, 1 partial, 2 fail |

Citation records are counted per returned excerpt, so two quotes referencing the
same chunk count twice. Provenance proves where a quote came from, not that it
answers the question. Source relevance is a filename check, not semantic
entailment. Manual comparison separately checks whether the quoted statements
meet the question's criteria. The lexical AND/OR groups provide a reproducible
coverage signal; they can miss paraphrases or reward misleading word matches.
They were individually reviewed for this run and happened to agree with manual
coverage. Future runs need fresh review; old response hashes cannot grade new
answers. Unsupported count zero applies only to these inspected answers, not a
general claim of hallucination freedom.

Latency excludes source verification, diagnostic retrieval, citation auditing and
the 65-second waits. The diagnostic call warms the embedding model/database
before agent timing; this is not a cold-start or load benchmark. There was one
run per question, so there are no variance estimates or statistically meaningful
population-level quality claims. Temperature zero does not make remote model
outputs permanently deterministic. The permissive similarity threshold 0.2
remained unchanged and does not guarantee relevant context.

## Actual failure analysis

### P03: supported but incomplete policy answer

Question: “What oversight and policy-formulation functions does Pakistan's Cyber
Governance Policy Committee (CGPC) have?”

Expected: strategic oversight; formulating/guiding/recommending the policy and
Act; updates and periodic reviews to align policy with emerging requirements
(policy PDF p. 11). Actual answer quoted only the first two responsibilities,
with valid p. 11 citations. This is **incomplete answer**, not fabricated citation.

Diagnostic top-five policy chunk indices were `[19, 24, 26, 12, 20]`.
Chunk 24 contains oversight/formulation; chunk 25 on the same PDF page contains:
“Guide to align policy with emerging cyberspace requirements through updates
and periodic reviews.” A direct read-only database check confirmed chunk 25 and
the raw PDF confirmed the criterion. Chunk 25 was absent from diagnostic top-k.
The evidence points to a page split plus ranking omission. A generator coverage
omission is also possible because selected prompt contents were not captured.
Future adjacent-chunk expansion or reranking merits evaluation; neither was
implemented in this milestone. This partial result remains unresolved.

### N03: answer exists but the relevant subcategory is not retrieved

Question: “Under NIST CSF 2.0 DE.AE-08, when are incidents declared?”

Expected, PDF p. 26: “Incidents are declared when adverse events meet the defined
incident criteria.” Actual response: “The available source evidence is
insufficient to answer this question reliably.” Citations: none. Status reason:
`model_abstained`. This is **incorrect abstention** relative to corpus ground
truth, while abstaining may be appropriate for the incomplete retrieved context.

Diagnostic NIST indices were `[76, 57, 77, 79, 26]`, on PDF pages
`[27, 20, 27, 28, 10]`. A direct database read found DE.AE-08 in index 75 on
p. 26; that chunk was missing from diagnostic results. This supports the
hypothesis that dense semantic retrieval fails to prioritize an exact framework
identifier. The safe provider response does not reveal its internal reasoning,
and diagnostic retrieval is separate from generation, so this is not proof of
the model's causal reasoning. Hybrid identifier search/reranking is a future
candidate. Unresolved; citation rules were not relaxed.

### C01: incident header retrieved without its outcome

Question: “In the CyberSage synthetic casebook CS-INC-002, how was ransomware
detected, contained, and recovered from, and was a ransom paid?”

Expected, casebook PDF p. 3: file renaming/unsigned encryption process; isolate
workstation and disable credentials; recover from verified offline backup;
no ransom payment. Actual answer was the same fixed insufficient-evidence
response, no citations, `model_abstained`: **incorrect abstention**.

Diagnostic casebook indices were `[4, 0, 31, 49, 7]`. Rank one, index 4, includes
CS-INC-002's header and detection. Direct database inspection confirmed index 5
on the same page contains containment, recovery and outcome, including “recovery
completed without ransom payment”; it was missing from top-five. The likely
failure is incomplete incident evidence across neighboring chunks. Expanding
neighbors or matching incident identifiers could help but requires later
evaluation. Unresolved. No unsupported incident answer was returned. The other
casebook answer, C02, explicitly labeled both excerpts synthetic and not real.

The machine-readable report retains diagnostic passages and the three direct
database source checks supporting these hypotheses. No provider errors,
rate-limit failures or citation rejections occurred in the ten recorded items.

## Separate risk and memory evidence

These demonstrations do not change the required ten-question dataset or its
metrics. The supplementary JSON records actual requests, results and citation
checks. Risk cases exercise Low, Medium, High and Critical; invalid inputs
exercise strict range/type validation. Scoring remains the existing illustrative
likelihood-times-impact matrix, not a prediction of real-world cyber loss.

Memory captures a real NIST incident-response question followed by “What about
recovery?”, the resolved follow-up, actual responses, citations and persisted
four-message history. Actual conversation/request IDs are access credentials
in this unauthenticated demonstration: they are captured only in ignored
`backend/.cache/evaluation-memory-private.json`. The public artifact records a
conversation-ID SHA-256 for correlation and masks the access ID. No unrestricted
conversation enumeration is introduced.

To reproduce persistence verification, stop the **local demonstration API**,
start it again with the same PostgreSQL configuration, then run:

```powershell
.\.venv\Scripts\python.exe -m evaluation.extra --verify-after-restart --output evaluation/results/new-supplementary.json
```

The verifier rereads the existing conversation and compares the complete history
with the private pre-restart snapshot. The flag itself does not restart a server.
Actual restart and demonstration results for this run are recorded below.

| Separate check | Actual result |
|---|---|
| Low | Likelihood 1 × impact 2 = 2, Low; no citations/model |
| Medium | 2 × 4 = 8, Medium; no citations/model |
| High | 3 × 5 = 15, High; no citations/model |
| Critical | 4 × 5 = 20, Critical; no citations/model |
| Invalid likelihood | 0, boolean `true`, and string `"4"` each rejected with HTTP 422 |
| Memory first turn | Answered with five verified NIST PDF p. 27 excerpts about response, incident management, plan execution, recovery criteria and analysis |
| Memory second turn | Resolved to `What does NIST CSF 2.0 say about recovery?`; `context_used: true`; insufficient evidence, `unsupported_evidence`, no citations |
| Conversation persistence | Four messages saved, original user messages preserved; complete history identical after API process restart |

The demonstration used `top_k: 1` (separate from the ten-question run's top five)
to keep live context small. Its second answer therefore demonstrates correct
resolution and safe abstention, **not successful recovery answering**. No
selected prompt or rejected draft was captured; `unsupported_evidence` alone
does not establish why the provider's support review rejected it. This limitation
remains unresolved and was not hidden by a rerun. The first answer's five
citations passed independent database and raw-PDF quote checks. API process
8944 was actually stopped and replaced by process 18320 before verifying
history equality; this was not merely a reread against the same process.

## Automated validation and commands executed

The final complete suite ran with real PostgreSQL integration tests enabled:
**332 passed**, including 28 added evaluation tests (dataset validation and PDF
checks, exact 8/2 split, result/error recording, independence, redaction, grading,
metrics, review binding, risk/memory helpers and a real PostgreSQL citation
audit). The suite's LLM calls were mocked; the live calls described above are
separate evidence. `pip check` reported **No broken requirements found**. No
dependencies or migrations were needed for this milestone.

Principal executed commands, from `backend/` unless stated otherwise:

```powershell
# API start (performed before evaluation and again for restart verification)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
.\.venv\Scripts\python.exe -m evaluation
.\.venv\Scripts\python.exe -m evaluation.extra
# Actual API process stop/restart occurred before this check:
.\.venv\Scripts\python.exe -m evaluation.extra --verify-after-restart
.\.venv\Scripts\python.exe -m evaluation.report
$env:CYBERSAGE_TEST_POSTGRES = '1'
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider --basetemp=.cache/pytest-milestone9-final
.\.venv\Scripts\python.exe -m pip check
# Repository root:
git diff --check
```

Additional read-only SQL inspected the missing neighboring chunks and counted
source documents/chunks. A local ignored review helper assembled the
individually inspected review notes and captured non-secret configuration after
the run; the public report renderer reproduces the Markdown from recorded
answers/reviews without further inference. Staged files were checked for secret
values and excluded paths before committing. Model weights, `.env`, PDFs,
virtual environments and the private memory snapshot remain ignored.

### Assignment screenshot instructions

No GUI screenshot was captured by this milestone. To create one locally after
the demo, open a PowerShell terminal in `backend/`:

```powershell
$demo = Get-Content .cache/evaluation-memory-private.json -Raw | ConvertFrom-Json
$demo.conversation_id
$demo.records | ForEach-Object {
    $_.question
    $_.response.resolved_message
    $_.response.status
    $_.response.answer
    $_.response.citations | Select-Object label, page_number, chunk_index
}
```

Use Windows Snipping Tool to capture the terminal showing both turns, resolved
follow-up and page citations. Save an actual image in a local assignment folder.
For a public report obscure the conversation ID; keep the private version only
for the assessor if necessary. Never include `.env`, database passwords, API
keys, or an environment-variable dump. A terminal screenshot is sufficient; no
frontend was implemented.

## Limitations

This is a small, fixed development evaluation, not a hidden holdout benchmark.
Expected criteria/rubric were authored with corpus access. Partial quoted answers
can omit important context even when every citation is genuine. Diagnostic
retrieval cannot prove the exact prompt selected by generation. The three
observed quality failures remain visible and unfixed. Future ranking/coverage
improvements must preserve citation validation and be evaluated in a separate
run. Conversation history is sensitive and access is currently based on knowing
a UUID; authentication remains outside scope.
