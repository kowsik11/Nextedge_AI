-- ================================================================
-- Google Sheets Integration - Database Migration (With Workspaces)
-- Run this in Supabase SQL Editor
-- ================================================================

-- STEP 1: Create workspaces table (if not exists)
-- This allows multi-tenant support (multiple users/organizations)
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Settings
    settings JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_workspace_name_per_owner UNIQUE(owner_id, name)
);

-- Create index for workspaces
CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces(owner_id);

-- Enable RLS for workspaces
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

-- Workspace policies: users can only see/manage their own workspaces
CREATE POLICY "Users can view their own workspaces"
    ON workspaces FOR SELECT
    USING (owner_id = auth.uid());

CREATE POLICY "Users can create their own workspaces"
    ON workspaces FOR INSERT
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY "Users can update their own workspaces"
    ON workspaces FOR UPDATE
    USING (owner_id = auth.uid());

CREATE POLICY "Users can delete their own workspaces"
    ON workspaces FOR DELETE
    USING (owner_id = auth.uid());

-- ================================================================
-- STEP 2: Create emails table (if not exists)
-- This stores all synced emails from Gmail
CREATE TABLE IF NOT EXISTS emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- Gmail identifiers
    message_id TEXT NOT NULL UNIQUE,  -- Gmail Message-ID
    thread_id TEXT,
    
    -- Email metadata
    subject TEXT,
    sender_email TEXT,
    sender_name TEXT,
    recipients JSONB DEFAULT '[]'::jsonb,  -- Array of email addresses
    
    -- Email content
    body_text TEXT,
    body_html TEXT,
    snippet TEXT,  -- Preview/excerpt
    
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

-- Create indexes for emails
CREATE INDEX IF NOT EXISTS idx_emails_workspace ON emails(workspace_id);
CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails(message_id);
CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id);
CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(processing_status);
CREATE INDEX IF NOT EXISTS idx_emails_gsheet_sync ON emails(synced_to_gsheets);

-- Enable RLS for emails
ALTER TABLE emails ENABLE ROW LEVEL SECURITY;

-- Email policies
CREATE POLICY "Users can view their workspace emails"
    ON emails FOR SELECT
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));

CREATE POLICY "Users can insert emails in their workspace"
    ON emails FOR INSERT
    WITH CHECK (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));

CREATE POLICY "Users can update their workspace emails"
    ON emails FOR UPDATE
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));

-- ================================================================
-- STEP 3: Create ai_analysis table (if not exists)
-- Stores AI classification results for emails
CREATE TABLE IF NOT EXISTS ai_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    
    -- AI classification results
    classification TEXT CHECK (classification IN ('Lead', 'Case', 'Contact', 'Opportunity', 'None')),
    confidence_score NUMERIC(3, 2) CHECK (confidence_score >= 0 AND confidence_score <= 1),  -- 0.0 to 1.0
    
    -- Additional AI insights
    urgency TEXT CHECK (urgency IN ('Low', 'Medium', 'High', 'Critical')),
    sentiment TEXT CHECK (sentiment IN ('Positive', 'Neutral', 'Negative')),
    intent TEXT,
    entities JSONB DEFAULT '[]'::jsonb,
    reasoning TEXT,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_email_analysis UNIQUE(email_id)
);

-- Create index for ai_analysis
CREATE INDEX IF NOT EXISTS idx_ai_analysis_email ON ai_analysis(email_id);
CREATE INDEX IF NOT EXISTS idx_ai_analysis_classification ON ai_analysis(classification);

-- Enable RLS for ai_analysis
ALTER TABLE ai_analysis ENABLE ROW LEVEL SECURITY;

-- AI analysis policies
CREATE POLICY "Users can view AI analysis for their emails"
    ON ai_analysis FOR SELECT
    USING (email_id IN (
        SELECT id FROM emails WHERE workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    ));

CREATE POLICY "Users can insert AI analysis for their emails"
    ON ai_analysis FOR INSERT
    WITH CHECK (email_id IN (
        SELECT id FROM emails WHERE workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    ));

-- ================================================================
-- STEP 4: Create google_sheets_connections table
CREATE TABLE IF NOT EXISTS google_sheets_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- OAuth tokens (encrypt these in application layer)
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scopes TEXT[],
    
    -- Sheet configuration
    spreadsheet_id TEXT NOT NULL,  -- The Google Sheet ID from URL
    spreadsheet_name TEXT,
    spreadsheet_url TEXT,
    
    -- Sync settings
    sync_mode TEXT DEFAULT 'manual' CHECK (sync_mode IN ('manual', 'automatic')),
    target_sheet_name TEXT DEFAULT 'Emails',  -- Which tab/sheet within spreadsheet
    
    -- Status
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expired', 'error', 'disconnected')),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_workspace_sheet UNIQUE(workspace_id, spreadsheet_id)
);

-- Create indexes for google_sheets_connections
CREATE INDEX IF NOT EXISTS idx_gsheets_workspace ON google_sheets_connections(workspace_id);
CREATE INDEX IF NOT EXISTS idx_gsheets_status ON google_sheets_connections(status);

-- Enable RLS
ALTER TABLE google_sheets_connections ENABLE ROW LEVEL SECURITY;

-- Google Sheets connection policies
CREATE POLICY "Users can view their workspace Google Sheets connections"
    ON google_sheets_connections FOR SELECT
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));

CREATE POLICY "Users can insert Google Sheets connections for their workspace"
    ON google_sheets_connections FOR INSERT
    WITH CHECK (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));

CREATE POLICY "Users can update their workspace Google Sheets connections"
    ON google_sheets_connections FOR UPDATE
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));

CREATE POLICY "Users can delete their workspace Google Sheets connections"
    ON google_sheets_connections FOR DELETE
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));

-- ================================================================
-- STEP 5: Create google_sheets_sync_log table
CREATE TABLE IF NOT EXISTS google_sheets_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES google_sheets_connections(id) ON DELETE CASCADE,
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    
    -- Sync details
    sheet_row_number INTEGER,  -- Which row was written in the sheet
    sync_status TEXT DEFAULT 'pending' CHECK (sync_status IN ('pending', 'success', 'failed', 'retrying')),
    error_message TEXT,
    
    -- Classification used for this sync
    classification_type TEXT CHECK (classification_type IN (
        'Lead', 'Case', 'Contact', 'Opportunity', 
        'Campaign', 'Deal', 'Order', 'Payment', 
        'Invoice', 'Quote', 'Task', 'Other'
    )),
    
    -- Timestamp
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Allow re-syncing same email to same connection
    CONSTRAINT unique_email_connection UNIQUE(connection_id, email_id)
);

-- Create indexes for google_sheets_sync_log
CREATE INDEX IF NOT EXISTS idx_gsheets_log_email ON google_sheets_sync_log(email_id);
CREATE INDEX IF NOT EXISTS idx_gsheets_log_status ON google_sheets_sync_log(sync_status);
CREATE INDEX IF NOT EXISTS idx_gsheets_log_connection ON google_sheets_sync_log(connection_id);
CREATE INDEX IF NOT EXISTS idx_gsheets_log_classification ON google_sheets_sync_log(classification_type);

-- Enable RLS
ALTER TABLE google_sheets_sync_log ENABLE ROW LEVEL SECURITY;

-- Sync log policies
CREATE POLICY "Users can view their workspace Google Sheets sync logs"
    ON google_sheets_sync_log FOR SELECT
    USING (connection_id IN (
        SELECT id FROM google_sheets_connections WHERE workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    ));

CREATE POLICY "Users can insert sync logs for their workspace"
    ON google_sheets_sync_log FOR INSERT
    WITH CHECK (connection_id IN (
        SELECT id FROM google_sheets_connections WHERE workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    ));

-- ================================================================
-- STEP 6: Create triggers for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to workspaces
DROP TRIGGER IF EXISTS trigger_workspaces_updated_at ON workspaces;
CREATE TRIGGER trigger_workspaces_updated_at
    BEFORE UPDATE ON workspaces
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to emails
DROP TRIGGER IF EXISTS trigger_emails_updated_at ON emails;
CREATE TRIGGER trigger_emails_updated_at
    BEFORE UPDATE ON emails
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to google_sheets_connections
DROP TRIGGER IF EXISTS trigger_gsheets_connections_updated_at ON google_sheets_connections;
CREATE TRIGGER trigger_gsheets_connections_updated_at
    BEFORE UPDATE ON google_sheets_connections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ================================================================
-- Migration Complete!
-- ================================================================
-- 
-- Tables created:
-- ✅ workspaces (for multi-tenant support)
-- ✅ emails (stores Gmail emails)
-- ✅ ai_analysis (AI classification results)
-- ✅ google_sheets_connections (OAuth + sheet config)
-- ✅ google_sheets_sync_log (sync tracking)
--
-- Features enabled:
-- ✅ Row Level Security (RLS) on all tables
-- ✅ Automatic timestamp updates
-- ✅ Workspace isolation
-- ✅ Proper foreign key relationships
--
-- Next steps:
-- 1. Create a workspace: INSERT INTO workspaces (name, owner_id) VALUES ('My Workspace', auth.uid());
-- 2. Use workspace_id when inserting emails and connections
-- ================================================================
