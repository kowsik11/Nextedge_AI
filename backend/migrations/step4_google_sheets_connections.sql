-- ================================================================
-- STEP 4: Create google_sheets_connections table
-- ================================================================

CREATE TABLE IF NOT EXISTS google_sheets_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- OAuth tokens (encrypt in application layer)
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scopes TEXT[],
    
    -- Sheet configuration
    spreadsheet_id TEXT NOT NULL,
    spreadsheet_name TEXT,
    spreadsheet_url TEXT,
    
    -- Sync settings
    sync_mode TEXT DEFAULT 'manual' CHECK (sync_mode IN ('manual', 'automatic')),
    target_sheet_name TEXT DEFAULT 'Emails',
    
    -- Status
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expired', 'error', 'disconnected')),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_workspace_sheet UNIQUE(workspace_id, spreadsheet_id)
);

CREATE INDEX IF NOT EXISTS idx_gsheets_workspace ON google_sheets_connections(workspace_id);
CREATE INDEX IF NOT EXISTS idx_gsheets_status ON google_sheets_connections(status);

ALTER TABLE google_sheets_connections ENABLE ROW LEVEL SECURITY;

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
