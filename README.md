# CyberSage

Cybersecurity RAG intelligence backend using Python 3.12, FastAPI, PostgreSQL 17,
and pgvector. This milestone indexes local PDFs; retrieval and a frontend are not
implemented yet.

## Local setup (PowerShell)

Create a repository-root `.env` using `.env.example` and set a nonempty local
password. For an existing database volume, use its existing credentials: changing
Compose variables does not change passwords stored in that volume. Never commit
`.env`, source PDFs, model weights, or virtual environments.

```powershell
docker compose up -d db
python -m venv backend/.venv
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

An existing backend environment can be reused. Settings load root `.env`, then
`backend/.env`, then process environment variables (highest priority). Optional
backend settings are shown in `backend/.env.example`. The default database address
is `127.0.0.1:5433`, matching Compose. When running the backend inside Docker, set
`POSTGRES_HOST=db` and `POSTGRES_PORT=5432`. Credentials are passed using
SQLAlchemy's URL builder, so special password characters need no manual escaping.

For a **new** database, apply the existing migration once from the repository root:

```powershell
Get-Content -Raw backend/migrations/001_initial_schema.sql | docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

The ingestion command never creates or changes schema. Check an existing database
from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m app.ingestion --check-db
```

## Ingest PDFs

Put the source PDFs in `data/raw/` (ignored by Git). From `backend/`:

```powershell
$env:HF_HOME = Join-Path (Get-Location) '.cache\huggingface'
.\.venv\Scripts\python.exe test_embeddings_manual.py
.\.venv\Scripts\python.exe -m app.ingestion
.\.venv\Scripts\python.exe -m app.ingestion --verify
```

The first model use may download `sentence-transformers/all-MiniLM-L6-v2`.
If the model is already fully cached and you need offline operation, set
`$env:HF_HUB_OFFLINE = '1'` before running the commands.
Subsequent calls in one process reuse the loaded model; subsequent processes reuse
downloaded weights. The model produces normalized vectors with 384 values.
`embed_texts(texts, batch_size=32)` encodes a list in order. Empty lists return `[]`;
blank texts, invalid types, and nonpositive batch sizes are rejected.

The CLI discovers `.pdf` files directly in `data/raw/`, sorted by name. It prints
per-file results and counts of documents processed/skipped, chunks inserted, and
failures. Override defaults with `--input-dir PATH --batch-size 16`. It returns a
nonzero exit code for failures, missing/empty input directories, or unsuccessful
verification. Errors show their type without printing SQL parameters or secrets.

SHA-256 identifies documents by file contents, so renamed copies are skipped after
indexing. Changed contents form a new document; existing records are not removed.
Failed/pending documents can be retried. A PostgreSQL transaction lock serializes
workers for the same hash. Each document uses its own transaction and savepoint:
chunk replacement and `indexed` status commit together, or processing writes roll
back and the document becomes `failed`. An interrupted process rolls back its
transaction. Other PDFs continue after a per-document failure. `processing` is an
intermediate transactional value, not a separately committed progress indicator.

Page references retain original PDF numbering, including gaps caused by blank
pages. `page_count` records total PDF pages. A PDF without extractable text fails;
OCR is not included. Verification reports both database-wide totals and records
matching current source hashes, checking dimensions, vector norms, page bounds,
duplicate chunk indices, and missing parent records. It does not delete any data.
For the original three source PDFs, the expected result is 3 indexed documents and
206 chunks. Other existing records may make database-wide totals larger.

## Tests

From `backend/`, ordinary unit tests require no model download or database:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider --basetemp=.cache/pytest-unit
```

Run PostgreSQL tests explicitly against the configured database:

```powershell
$env:CYBERSAGE_TEST_POSTGRES = '1'
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider --basetemp=.cache/pytest-postgres
Remove-Item Env:CYBERSAGE_TEST_POSTGRES
```

Integration tests reuse the real migration constraints in temporary tables and
roll back their transactions; existing document data is untouched. They test real
pgvector writes, duplicate handling, page references, foreign keys, dimension
constraints, rollback after partial writes, and retries. Real-model behavior is
checked separately by the smoke script and end-to-end ingestion.

Start the API from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The existing health endpoint is `GET /api/v1/health`.

## Milestone 4 validation (2026-11-12)

Validated locally with PostgreSQL 17.11, pgvector 0.8.7, SQLAlchemy 2.1.8,
psycopg 3.3.8, and sentence-transformers 6.3.0:

- Full suite: **45 passed**, including five real PostgreSQL integration tests.
- Ordinary offline suite: **40 passed, 5 integration tests skipped** as intended.
- Real-model smoke test: 384 dimensions, L2 norm 1.000000.
- Database baseline: 0 documents, 0 chunks. No existing records were removed.
- First ingestion: 3 documents indexed, 206 chunks inserted, 0 failures.
- Second ingestion: 3 documents skipped, 0 chunks inserted, 0 failures.
- Stored documents: national policy 22 pages / 52 chunks, incident casebook
  21 pages / 61 chunks, NIST CSF 32 pages / 93 chunks. All have status `indexed`.
- Verification: 0 invalid dimensions, page references, vector norms, duplicate
  indices, or orphan chunks. Database totals remained 3 documents / 206 chunks.
- Existing health endpoint, `pip check`, and `git diff --check` passed.

Windows denied access to pytest's default temporary directory in one initial
integration run; the documented project-local `--basetemp` resolved it. Hugging
Face metadata requests were restricted in the sandbox; the real smoke test passed
with approved network access, and ingestion used the fully cached model offline.
