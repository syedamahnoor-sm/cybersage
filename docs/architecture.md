# CyberSage architecture

This diagram describes the implemented local application at Milestone 11,
not a proposed deployment. The final submission preserves that implementation.
See the [final report](CyberSage_Final_Assignment_Report.md) and
[integration evidence](milestone11-integration.md).

## System and data flow

```mermaid
flowchart TB
    subgraph Browser["Browser — Next.js interface"]
        UI["Overview · Assistant · Risk Analyzer · Knowledge Base · About"]
        Client["Typed API client + runtime response checks"]
        Shortcuts["Local shortcuts: conversation IDs, titles, timestamps"]
        Preview["Illustrative local risk preview"]
        UI --> Client
        UI <--> Shortcuts
        UI --> Preview
    end

    Proxy["Next.js same-origin /api/v1 rewrite"]
    API["FastAPI: validation and safe HTTP errors"]
    Memory["ConversationService: bounded history, request replay, atomic completed turns"]
    Graph["LangGraph StateGraph: validate → resolve → select"]
    RAG["RAG service: fresh retrieval and bounded evidence selection"]
    Embed["Cached local all-MiniLM-L6-v2: normalized 384-dimensional embeddings"]
    Search["Parameterized cosine-distance search and document metadata join"]
    Provider["Replaceable LLM adapter: official Groq SDK"]
    Groq["Groq: openai/gpt-oss-120b"]
    Verify["Exact-quote and evidence-ID checks + provider support/relevance verdict"]
    Risk["Pure deterministic tool: likelihood × impact, ratings 1–5"]
    Format["Structured response: answer or assessment, status, citations, IDs"]
    Abstain["Insufficient evidence: explicit abstention, no citations"]

    subgraph PG["Existing PostgreSQL 17 + pgvector database"]
        Corpus[("documents + document_chunks: VECTOR 384")]
        History[("conversations + conversation_turns + conversation_messages")]
    end

    Client --> Proxy --> API --> Memory
    Memory <--> History
    Memory --> Graph
    Graph -->|knowledge| RAG
    Graph -->|risk with complete current inputs| Risk
    Graph -->|invalid or ambiguous| Format
    RAG --> Embed --> Search
    Search <--> Corpus
    Search --> RAG
    RAG -->|selected evidence only| Provider
    Provider <--> Groq
    Provider --> Verify
    RAG -->|no usable evidence| Abstain
    Verify -->|supported source excerpts| Format
    Verify -->|rejected or insufficient| Abstain --> Format
    Risk --> Format
    Format -->|successful completed turn| Memory
    Memory -->|response| API --> Proxy --> Client

    PDFs["Three local PDFs, excluded from Git"]
    Ingest["Explicit ingestion CLI: SHA-256 → page extraction → chunks → batch embeddings"]
    PDFs --> Ingest
    Ingest --> Embed
    Ingest -->|idempotent transactional inserts| Corpus
```

The arrows between storage and services represent reads/writes, not graph
execution loops. The browser never calls Groq or PostgreSQL directly. Provider
credentials remain in the existing backend environment. Next.js supplies a
transport rewrite, not a second domain backend.

## Bounded agent transitions

```mermaid
flowchart LR
    START --> validate
    validate -->|valid| resolve
    validate -->|invalid| error
    resolve -->|resolved or standalone| select
    resolve -->|ambiguous| error
    select -->|knowledge| rag
    select -->|risk| risk
    select -->|missing or conflicting inputs| error
    rag -->|answer or abstention| format
    risk -->|assessment| format
    rag -->|service failure| error
    risk -->|invalid inputs| error
    error --> format
    format --> END
```

This is one acyclic agent, with an eight-step recursion guard. There are no
autonomous shell/network tools, multi-agent loops or graph checkpointers.
Conversation persistence is implemented outside the graph in PostgreSQL.

## Trust boundaries

- User messages and PDF text are untrusted. PDFs are evidence, not executable
  instructions. Only selected passages within configured budgets reach Groq.
- Stable evidence IDs are assigned locally. Citation titles, filenames, physical
  PDF pages and chunk indices come from stored metadata, not model guesses.
- Exact quote provenance and valid IDs are necessary but do not prove factual
  entailment or complete coverage. Unsupported output can cause abstention.
- Recent user context resolves follow-ups before fresh retrieval. Prior assistant
  prose is not source evidence; risk numbers are not inherited from earlier turns.
- The backend is authoritative for confirmed risk results. The frontend's
  preview is separately labeled and cannot override the submitted result.
- Conversation IDs grant history access without authentication. The interface
  exposes no list-all-conversations endpoint. This is a local research system.

Implementation references: [agent graph](../backend/app/agent/service.py),
[RAG](../backend/app/rag/service.py), [memory](../backend/app/memory/service.py),
[retrieval](../backend/app/retrieval/service.py),
[API client](../frontend/src/lib/api.ts).
