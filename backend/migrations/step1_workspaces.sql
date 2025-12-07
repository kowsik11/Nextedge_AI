-- ================================================================
-- STEP 1: Create workspaces table
-- ================================================================

CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_workspace_name_per_owner UNIQUE(owner_id, name)
);

CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces(owner_id);

ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own workspaces"
    ON workspaces FOR SELECT USING (owner_id = auth.uid());

CREATE POLICY "Users can create their own workspaces"
    ON workspaces FOR INSERT WITH CHECK (owner_id = auth.uid());

CREATE POLICY "Users can update their own workspaces"
    ON workspaces FOR UPDATE USING (owner_id = auth.uid());

CREATE POLICY "Users can delete their own workspaces"
    ON workspaces FOR DELETE USING (owner_id = auth.uid());
