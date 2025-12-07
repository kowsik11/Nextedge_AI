-- ================================================================
-- STEP 5: Create google_sheets_sync_log table
-- ================================================================

CREATE TABLE IF NOT EXISTS google_sheets_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES google_sheets_connections(id) ON DELETE CASCADE,
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    
    -- Sync details
    sheet_row_number INTEGER,
    sync_status TEXT DEFAULT 'pending' CHECK (sync_status IN ('pending', 'success', 'failed', 'retrying')),
    error_message TEXT,
    
    -- Classification used for this sync
    classification_type TEXT CHECK (classification_type IN (
        'Lead', 'Case', 'Contact', 'Opportunity', 
        'Campaign', 'Deal', 'Order', 'Payment', 
        'Invoice', 'Quote', 'Task', 'Other'
    )),
    
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_email_connection UNIQUE(connection_id, email_id)
);

CREATE INDEX IF NOT EXISTS idx_gsheets_log_email ON google_sheets_sync_log(email_id);
CREATE INDEX IF NOT EXISTS idx_gsheets_log_status ON google_sheets_sync_log(sync_status);
CREATE INDEX IF NOT EXISTS idx_gsheets_log_connection ON google_sheets_sync_log(connection_id);
CREATE INDEX IF NOT EXISTS idx_gsheets_log_classification ON google_sheets_sync_log(classification_type);

ALTER TABLE google_sheets_sync_log ENABLE ROW LEVEL SECURITY;

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
