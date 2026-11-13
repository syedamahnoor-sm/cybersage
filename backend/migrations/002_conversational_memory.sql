-- Apply explicitly with psql -v ON_ERROR_STOP=1. No document tables are changed.
BEGIN;

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE conversation_turns (
    request_id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL CHECK (turn_number > 0),
    request_hash VARCHAR(64) NOT NULL CHECK (length(request_hash) = 64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (conversation_id, turn_number),
    UNIQUE (conversation_id, request_id)
);

CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    request_id UUID NOT NULL,
    role VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 20000),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (conversation_id, request_id)
        REFERENCES conversation_turns(conversation_id, request_id) ON DELETE CASCADE,
    UNIQUE (request_id, role)
);

CREATE INDEX idx_conversation_messages_conversation ON conversation_messages(conversation_id);

COMMIT;
