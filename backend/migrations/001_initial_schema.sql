CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    filename VARCHAR(255) NOT NULL,
    title VARCHAR(500),

    source VARCHAR(255),
    jurisdiction VARCHAR(100),

    file_hash VARCHAR(64) NOT NULL UNIQUE,
    page_count INTEGER CHECK (page_count > 0),

    status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (
            status IN (
                'pending',
                'processing',
                'indexed',
                'failed'
            )
        ),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_id UUID NOT NULL
        REFERENCES documents(id) ON DELETE CASCADE,

    chunk_index INTEGER NOT NULL
        CHECK (chunk_index >= 0),

    page_number INTEGER NOT NULL
        CHECK (page_number > 0),

    content TEXT NOT NULL
        CHECK (length(trim(content)) > 0),

    embedding VECTOR(384) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document
ON document_chunks(document_id);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding
ON document_chunks
USING hnsw (embedding vector_cosine_ops);
