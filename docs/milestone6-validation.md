# Milestone 6 validation

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

## Live Groq status: pending credentials

No `GROQ_API_KEY` was found in process or configured root/backend environment
files. The explicit `test_rag_manual.py` check printed
`live_llm_status=skipped_missing_credentials`. **No live Groq answer, unanswerable
question result, rate-limit behavior, latency, or account-model availability is
claimed as validated.**

The configurable default `openai/gpt-oss-120b` was selected using Groq's current
[supported model documentation](https://console.groq.com/docs/models) and
[deprecation notices](https://console.groq.com/docs/deprecations). The adapter
validates the configured model through Groq's models endpoint on first use with
credentials. Public documentation is not proof of availability for an account.

Once credentials are supplied, the manual script asks the three original corpus
questions and an unanswerable question requesting the exact malware SHA-256 for
CS-INC-002. It checks citations against the actual raw PDF page text and requires
abstention on the hash question. Results still require manual relevance review.

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
