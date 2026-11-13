# Milestone 8: persistent conversational memory validation

## Schema and application architecture

Migration `002_conversational_memory.sql` was explicitly applied to the existing
PostgreSQL 17 database in one transaction. It adds `conversations`,
`conversation_turns`, and `conversation_messages`; no document or vector schema
was changed. Inspection confirmed the expected UUIDs, revisions, timestamps,
request fingerprints, role/content/JSON checks, unique turn/request/role keys,
and composite conversation/request foreign key. Startup does not apply migrations.

ConversationService reads a bounded, conversation-filtered snapshot, invokes the
existing graph, and atomically saves a completed user/assistant pair and public
response metadata. Short transactions end before model calls. Final writes compare
the revision, so concurrent turns cannot silently overwrite or mix their contexts.
Stale writers get 409, and duplicate committed request IDs replay the stored
response. Storage failures roll back the entire turn and withhold unsaved answers.
Provider/graph errors and invalid inputs create neither incomplete messages nor
empty new conversations. Honest clarification/insufficient-evidence turns persist.

The graph is now validate → resolve → select → RAG/risk → format → END; errors
pass through the existing error node. The fixed eight-step guard remains; normal
paths have five nodes and a RAG failure has six. LangGraph checkpoints are not
used. The resolver reads recent user/resolved questions and capability/status
metadata, never assistant answer prose or citation quotes. It deterministically
resolves a limited set of named-source references; ambiguous references ask for
clarification. New knowledge turns always call existing RAG with the resolved
question for fresh retrieval. Risk never inherits prior numerical inputs.

Memory defaults to six recent turns and 8000 characters of user/resolved question
projection. Full stored answers are available only through bounded history pages,
not as factual model context. History persists across application restarts.

## Automated results

- Full suite with real PostgreSQL: **304 passed**, including **23 PostgreSQL
  tests**. Offline suite: **281 passed, 23 PostgreSQL tests intentionally skipped**.
- Tests cover turn creation, timestamps/roles, original-message persistence,
  source-scoped resolution, standalone questions, bounded history/pagination,
  unknown IDs, isolation, API backward compatibility, citation preservation,
  risk independence, committed request replay, changed-input/target conflicts,
  racing new-conversation retries, stale revisions, and transaction rollback for
  both new and existing conversations after a failing message insertion.
- API/storage/provider failures are sanitized. Tests reject obvious Groq-key
  messages before invoking storage or inference. Only public response metadata
  is persisted; provider/system prompts are never stored.
- Ordinary API tests use isolated memory fakes; PostgreSQL tests apply both exact
  migrations to temporary tables and roll back. Existing conversation/document
  records are untouched by these automated tests.
- `pip check`, manual-script syntax checks, and Git whitespace checks passed.
  No dependency installation or requirements changes were needed.

## Actual live, two-process validation

Groq `openai/gpt-oss-120b`, real MiniLM retrieval, PostgreSQL, the LangGraph agent,
and the real HTTP API were used without mocked inference or dependencies. Initial
turns ran in Uvicorn process **31852**. It was stopped, and follow-ups/history checks
ran in a new Uvicorn process **29812**. The provider was paced 65 seconds between
questions. Conversation/request IDs and scrubbed reports remain in ignored
`backend/.cache/milestone8-live.json`; live access identifiers are not published here.

An initial sandboxed server request returned HTTP 503 before successful live
validation. It saved no turn. Restarting with approved provider network access
resolved the environment restriction; no citation checks were relaxed.

### Conversation A

1. **Original:** `What does NIST CSF 2.0 say about incident response?`
   HTTP **200**, `answered`, `context_used=false`, top-k **1**. Actual excerpts
   included RESPOND/incident-management definitions, RS.MA-01 response-plan
   execution with relevant third parties, recovery-initiation criteria, and
   incident analysis/forensics. All five citations were
   `[NIST.CSWP.29.pdf, p. 27]`, chunk index **76**, evidence
   `E_45eebff5cd2b40b6879df1161f0d7452`. Time: **58.29 s**, including initial
   embedding/application warm-up and citation checks.
2. **After restart, original:** `What about recovery?`
   **Resolved:** `What does NIST CSF 2.0 say about recovery?`
   HTTP **200**, `answered`, `context_used=true`, top-k **1**. Time: **21.24 s**
   including cold embedding startup in the new server and citation checks.
   The fresh result moved to `[NIST.CSWP.29.pdf, p. 28]`, chunk index **79**,
   evidence `E_b4fe26f3294d4a62abaccaa24ef67707`. Actual excerpts were:

   > RC.RP-02: Recovery actions are selected, scoped, prioritized, and performed

   > RC.RP-03: The integrity of backups and other restoration assets is verified before using them for restoration

   > RC.RP-04: Critical mission functions and cybersecurity risk management are considered to establish post-incident operational norms

   > RC.RP-05: The integrity of restored assets is verified, systems and services are restored, and normal operating status is confirmed

   > RC.RP-06: The end of incident recovery is declared based on criteria, and incident- related documentation is completed

These are relevant, source-supported recovery excerpts, not a complete account
of all CSF recovery guidance. The original follow-up text remains the stored user
message; only separate response metadata records the contextual rewrite.

### Conversation B

1. **Original:** `What does Pakistan's National Cyber Security Policy say about critical infrastructure?`
   HTTP **200**, `answered`, `context_used=false`, top-k **5**, **2.68 s**.
   Actual quote, rendered as `Policy source`:

   > Will regard a cyber-attack on Pakistan CI/ CII as an act of aggression against national sovereignty and will defend itself with appropriate response measures.

   Citation `[2021-National-Cyber-Security-Policy-Final.pdf, p. 11]`, chunk
   index **24**, evidence `E_25a5728633a04d78928c5daeaaf524c9`.
2. **After restart, original:** `What response measures does it describe?`
   **Resolved:** `What response measures does Pakistan's National Cyber Security Policy describe?`
   HTTP **200**, `answered`, `context_used=true`, top-k **5**, **4.06 s**. Fresh
   retrieval and generation selected the same source-supported CI/CII response
   quote on PDF page **11**, with the same chunk metadata. It did not use NIST
   context or import Conversation A's recovery statements. The passage mentions
   appropriate response measures but does not enumerate specific actions; the
   answer preserves that limitation rather than inventing them.

## Persistence, isolation, and consistency checks

- All four turns answered. **12 citation records** across three distinct chunks
  matched database document/chunk UUIDs, filename/title, PDF page, chunk index,
  stable evidence ID, original stored text, and extracted raw PDF page text.
- After stopping the first process, each conversation's first two messages were
  readable in the new process before any new inference. Replaying both original
  request IDs returned exactly the original response/ID with no new messages.
- Final histories contained exactly **four messages per conversation**, alternating
  user/assistant. Stored user messages matched their two original requests,
  including the unresolved follow-ups. A resolved only against NIST, B only
  against Pakistan's policy. Neither conversation's messages appeared in the other.
- Final database memory totals: **2 conversations, 4 turns, 8 messages**. Explicit
  cross-conversation reuse of A's request ID with B's ID returned **409**, without
  exposing A's response or writing anything. Unknown conversation POST and GET
  returned **404**. The conversation-enumeration URL returned **404**.
- Live `limit=1` history returned one complete turn with a backward cursor; the
  cursor retrieved the earlier turn. No unrestricted history/list endpoint exists.
- Document verification retained **3 indexed documents / 206 chunks**, with zero
  invalid dimensions, vector norms, page references, orphan chunks, or duplicate
  indices. Ingestion rerun skipped the three existing documents.

## Privacy and limitations

Authentication/ownership is still absent: knowledge of a conversation ID grants
read/continue access, and a request ID can recover its original response. These
UUIDs provide scoping, not authorization. Access URLs may be logged. Restrict this
to local demonstration and avoid confidential data until authentication and
retention controls exist. No conversation IDs or credentials are committed in
this report; raw PDFs and diagnostic reports remain ignored.

The deterministic resolver supports only straightforward named-source follow-ups,
not general pronoun/topic understanding. It does not inherit facts from assistant
answers or risk numbers. History bounds limit context, not total durable storage;
there is no automatic expiration. Credential-pattern rejection is not a general
secret/PII detector. Original messages retain the API's existing trimming behavior.

Optimistic concurrency can spend duplicate model work before a stale turn gets
409; clients should serialize turns. Reliable retry deduplication requires a stable
client-generated request ID; it cannot be guaranteed when a generated ID and the
first response are both lost. Successful committed requests are replayed, while
failed calls can be retried. Stored citations are historical, not automatically
revalidated by the history endpoint; new turns retrieve fresh evidence.

Existing exact-quote/relevance checks can still cause conservative abstention,
and quotes/provenance do not prove source truth, exhaustive coverage, or factual
entailment. These four live turns are a small functional smoke test, not a memory
or retrieval benchmark. Existing provider timeouts and the eight-step graph guard
remain in force. No multi-agent system, profiling, frontend, authentication,
autonomous actions, or deployment was added.
