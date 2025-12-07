-- ================================================================
-- STEP 2: Create emails table
-- ================================================================

CREATE TABLE IF NOT EXISTS emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- Gmail identifiers
    message_id TEXT NOT NULL UNIQUE,
    thread_id TEXT,
    
    -- Email metadata
    subject TEXT,
    sender_email TEXT,
    sender_name TEXT,
    recipients JSONB DEFAULT '[]'::jsonb,
    
    -- Email content
    body_text TEXT,
    body_html TEXT,
    snippet TEXT,
    
    -- Metadata
    received_at TIMESTAMP WITH TIME ZONE,
    has_attachments BOOLEAN DEFAULT FALSE,
    labels TEXT[] DEFAULT '{}',
    
    -- Processing status
    processing_status TEXT DEFAULT 'new' CHECK (processing_status IN ('new', 'processing', 'processed', 'error')),
    synced_to_salesforce BOOLEAN DEFAULT FALSE,
    synced_to_hubspot BOOLEAN DEFAULT FALSE,
    synced_to_gsheets BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_emails_workspace ON emails(workspace_id);
CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails(message_id);
CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id);
CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(processing_status);
CREATE INDEX IF NOT EXISTS idx_emails_gsheet_sync ON emails(synced_to_gsheets);

ALTER TABLE emails ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their workspace emails"
    ON emails FOR SELECT
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));

CREATE POLICY "Users can insert emails in their workspace"
    ON emails FOR INSERT
    WITH CHECK (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));

CREATE POLICY "Users can update their workspace emails"
    ON emails FOR UPDATE
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));
