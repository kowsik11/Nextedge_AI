-- ================================================================
-- STEP 6: Create triggers for automatic timestamp updates
-- ================================================================

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
