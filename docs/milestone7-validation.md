# Milestone 7: bounded agent and illustrative risk scoring

## Architecture and routing

The FastAPI agent endpoint invokes one LangGraph `StateGraph`, compiled without
checkpointing, persistent stores, or loop edges. State is an explicit `TypedDict`;
API inputs, responses, errors, and risk parameters use Pydantic schemas. Each
invocation starts fresh and returns only its public formatted response.

Nodes: `validate`, `select`, `rag`, `risk`, `error`, `format`.

- Normal knowledge: START → validate → select → rag → format → END.
- Normal risk: START → validate → select → risk → format → END.
- Missing/ambiguous/invalid requests: validation or selection → error → format → END.
- Operational RAG errors: rag → error → format → END, preserving safe 503/504 behavior.
- A hard recursion limit of **8** is set by the service, never by user text. The
  ordinary paths execute four nodes; a RAG failure executes five. Unexpected
  graph/step-limit failures return safe 500 responses, without raw state/exceptions.

Routing is deterministic, with no classification LLM. Source-related questions
select existing RAG. Explicit numerical risk commands/fields select the pure
scoring tool. Mixed source-and-calculation requests, unknown messages, repeated
labels, or conflicting structured/text numbers require clarification. Labeled
inline digits are supported; missing and unlabeled numbers are never guessed.
This conservative English keyword/label parser is limited and can require rephrasing.

The RAG node lazily composes existing retrieval/RAG factories. It reuses the same
database engine, Groq provider, citation validation, prompts, source typing,
abstention behavior, and application shutdown lifecycle. Risk never creates a
database/provider resource, calls a model, or returns PDF citations. No shell,
filesystem, arbitrary-network, dynamic execution, or user-selected tools exist.
Retrieved text cannot select another tool: the RAG path ends at formatting.

## Risk verification

Score = integer likelihood × integer impact, each 1..5. Categories: Low 1..5,
Medium 6..10, High 11..15, Critical 16..25. All **25 valid matrix cells** are tested,
along with strict rejection of booleans, floats, numeric strings, missing/invalid
values, ambiguous text, conflicts, and attempted textual score overrides.

This is an illustrative qualitative matrix, **not a validated prediction of
real-world cyber risk**, calibrated probability, loss estimate, or compliance
assessment. Interpretations repeat the supplied scales and resulting category;
the LLM cannot compute or alter any assessment field.

## Automated and database validation

- Full suite with `CYBERSAGE_TEST_POSTGRES=1`: **269 passed** (165 preexisting
  tests plus 104 agent/risk tests), including **13 real PostgreSQL tests**.
- Ordinary offline suite: **256 passed, 13 PostgreSQL tests intentionally skipped**.
- Exact graph paths, explicit termination, absent checkpointing, the recursion
  guard, no cross-request memory, one RAG invocation, and no risk-to-LLM calls
  are tested. Provider/retrieval exceptions remain sanitized and correctly routed.
- Real PostgreSQL integration exercises API → graph → existing RAG → pgvector,
  with only inference mocked. Document UUID, physical PDF page 27, chunk index,
  quote, and citation label survive unchanged. A subsequent risk invocation makes
  zero additional provider calls.
- The initial integration test used an eager FastAPI override that did not apply
  to the lazy factory composition. The fixture was corrected to patch the lazy
  factory to isolated temporary tables; the integration test then passed.
- API tests cover body structure, request length, strict numeric bounds, optional
  top-k bounds, missing/conflicting/ambiguous requests, safe 422/503/504 responses,
  and absence of graph state or secret exception details in public JSON.
- `pip check` passed; installed LangGraph version is **1.2.21**. No existing
  dependency was removed. The deprecated iterator-style parametrization warning
  in an early new test was corrected; the final suite had no such warning.
- Ingestion rerun: **3 skipped, 0 chunks inserted, 0 failures**. Verification
  retained **3 indexed documents / 206 chunks**, with no invalid dimensions,
  norms, page references, orphan chunks, or duplicate indices.

## Live diagnostic: conservative RAG abstention

The first agent smoke run reached `capability=knowledge` for
`What does NIST CSF 2.0 say about incident response?`, but returned HTTP 200,
`status=insufficient_evidence`, reason `unsupported_evidence`. The strict smoke
assertion correctly failed rather than claiming the question was answered.

A diagnostic rerun confirmed selection returned three cited excerpts. Two matched
verbatim; the third changed a source's mid-sentence lowercase `actions` to initial
uppercase `Actions`. The case-sensitive quote membership gate rejected the entire
answer before review. No graph routing failure or unsupported citation was exposed.
The agent preserved this safe abstention from existing RAG exactly as required.

No retrieval threshold, quotation check, citation validation, RAG prompt, or
provider behavior was relaxed. The final live smoke uses the previously validated
question `How does NIST CSF 2.0 address incident response?`. The initial phrasing's
false abstention remains a documented RAG coverage limitation, not hidden success.

An initial smoke attempt with the alternate `How does...` phrasing at top-k 5 also
abstained and failed its strict answered assertion. A later paced diagnostic run
of the same question at the same top-k **did answer**, without any RAG code change.
The later results do not erase the earlier failures. Low temperature does not
make generation or quote selection reliably identical across live requests.

## Actual live agent results

Live checks used the FastAPI application via TestClient, the actual LangGraph,
real PostgreSQL/pgvector and MiniLM retrieval, and configured Groq model
`openai/gpt-oss-120b`. No inference, graph routing, or database output was mocked.
Only a diagnostic wrapper recorded scrubbed inputs/outputs while calling the
original provider unchanged. Reports remain in ignored `backend/.cache/`.

### Deterministic risk and validation paths

All four requests selected `risk`, returned HTTP 200 and `status=assessed`, with
`model=null` and `citations=[]`:

| Likelihood | Impact | Actual score | Actual category |
|---:|---:|---:|---|
| 1 | 2 | 2 | Low |
| 2 | 4 | 8 | Medium |
| 3 | 5 | 15 | High |
| 4 | 5 | 20 | Critical |

The critical interpretation was:

> Likelihood 4/5 and impact 5/5 produce 20/25, classified as Critical in this illustrative matrix.

Every result included the illustrative-matrix disclaimer. No LLM was used in the
risk path. Likelihood 6 / impact 5 returned HTTP **422**. `Calculate risk` without
numbers returned HTTP **200**, `missing_input`, with missing fields `likelihood`
and `impact`. `Do something` returned HTTP **200**, `needs_clarification`, selected
capability `none`. Neither missing/ambiguous request produced an assessment or
citations.

### Grounded knowledge, default context

Question: `How does NIST CSF 2.0 address incident response?`, top-k **5**.
The later paced comparison returned HTTP **200**, `capability=knowledge`,
`status=answered`, five retrieved/selected chunks, and model `openai/gpt-oss-120b`.
Time was **25.25 seconds**, including cold embedding startup; this is a single
observation, not a latency benchmark.

The actual answer rendered these five excerpts with `Framework guidance:` and
`[NIST.CSWP.29.pdf, p. 27]`:

> RESPOND (RS): Actions regarding a detected cybersecurity incident are taken

> Incident Management (RS.MA): Responses to detected cybersecurity incidents are managed

> RS.MA-01: The incident response plan is executed in coordination with relevant third parties once an incident is declared

> Incident Analysis (RS.AN): Investigations are conducted to ensure effective response and support forensics and recovery activities

> RS.MA-05: The criteria for initiating incident recovery are applied

All five citation records referred to document
`7bc85d48-0606-4e6b-aa7e-f453e59cca0a`, chunk
`45eebff5-cd2b-40b6-879d-f1161f0d7452`, chunk index **76**, evidence ID
`E_45eebff5cd2b40b6879df1161f0d7452`. Each quote and metadata field matched
PostgreSQL and the original PDF's physical page **27**. Manual review found the
excerpts relevant and source-supported; they are a partial overview rather than
all incident-response guidance. No numerical risk assessment or invented source
was added by the agent.

### Narrow-context comparison and unanswerable question

The same NIST question at top-k **1** also returned HTTP **200**, `knowledge`,
`answered`, in **5.51 seconds**. It retrieved/selected one chunk and produced
five citation records for the same NIST document/page/index/ID. Its excerpts were
RESPOND's definition, incident management's definition, RS.MA-01, RS.MA-02
(triage/validation), and RS.AN-03 (incident/root-cause analysis). All five were
checked against the database and physical PDF page 27. This is a comparison using
the existing top-k option; neither the API default nor RAG logic was changed.
The reusable live smoke script uses top-k 1 for this grounded question to reduce
the number of passages from which the model can produce altered excerpts.

`What is the cybersecurity policy of Mars in 2050?`, top-k **5**, returned HTTP
**200**, `capability=knowledge`, `status=insufficient_evidence`, reason
`model_abstained`, in **2.11 seconds**:

> The available source evidence is insufficient to answer this question reliably.

It retrieved/selected five chunks but returned `citations=[]`, `assessment=null`,
and no invented policy or risk score. The agent preserved RAG's abstention exactly.

The completed diagnostic smoke run recorded **10 API requests**: four risk
assessments, invalid risk, missing inputs, ambiguous input, two NIST context
variants, and Mars. All expected statuses and scores were verified. Across the
two answered NIST requests, **10 citation records** referenced one distinct stored
chunk and passed database metadata, stable-ID, exact-quote, and raw PDF page-text
checks. No credential was printed, logged, staged, or committed. This final paced
run had no provider errors; initial abstentions and smoke assertion failures are
retained above. Provider timeout/rate-limit behavior was exercised in mocked tests,
not induced against the live account in this milestone.

## Known limitations

English deterministic routing does not provide general intent understanding;
mixed requests are deliberately not split into multiple tools. The risk matrix
is illustrative and relies on user-supplied scales. Graph step limits do not
bound model startup time or total network latency; existing provider timeouts and
rate limits still apply. Exact-quote RAG checks can abstain on minor formatting
changes, and same-model relevance review remains fallible. Single-question smoke
results do not establish general answer completeness or factual entailment.

No multi-agent orchestration, conversation memory, authentication, frontend,
external automation, or deployment was implemented.
