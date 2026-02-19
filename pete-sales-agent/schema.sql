-- Pete Sales Agent — Supabase schema for conversation tracking

-- Conversations table (one row per email thread)
CREATE TABLE IF NOT EXISTS pete_conversations (
    id BIGSERIAL PRIMARY KEY,
    thread_id TEXT UNIQUE NOT NULL,
    prospect_email TEXT NOT NULL,
    prospect_name TEXT,
    subject TEXT,
    first_intent TEXT,
    last_intent TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'demo_booked', 'escalated', 'closed_won', 'closed_lost', 'nurture')),
    message_count INT DEFAULT 0,
    demo_requested_at TIMESTAMPTZ,
    escalated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    last_message_at TIMESTAMPTZ DEFAULT now()
);

-- Messages table (individual messages within threads)
CREATE TABLE IF NOT EXISTS pete_messages (
    id BIGSERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES pete_conversations(thread_id),
    message_id TEXT,
    sender TEXT NOT NULL,
    body TEXT,
    intent TEXT,
    response_sent TEXT,
    inbound BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_status ON pete_conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_email ON pete_conversations(prospect_email);
CREATE INDEX IF NOT EXISTS idx_messages_thread ON pete_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON pete_messages(created_at);

-- Enable RLS
ALTER TABLE pete_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE pete_messages ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (Pete uses service key)
CREATE POLICY "service_role_conversations" ON pete_conversations
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "service_role_messages" ON pete_messages
    FOR ALL USING (true) WITH CHECK (true);
