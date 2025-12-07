-- ================================================================
-- STEP 3: Create ai_analysis table
-- ================================================================

CREATE TABLE IF NOT EXISTS ai_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    
    -- AI classification results
    classification TEXT CHECK (classification IN ('Lead', 'Case', 'Contact', 'Opportunity', 'None')),
    confidence_score NUMERIC(3, 2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    -- Additional AI insights
    urgency TEXT CHECK (urgency IN ('Low', 'Medium', 'High', 'Critical')),
    sentiment TEXT CHECK (sentiment IN ('Positive', 'Neutral', 'Negative')),
    intent TEXT,
    entities JSONB DEFAULT '[]'::jsonb,
    reasoning TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_email_analysis UNIQUE(email_id)
);

CREATE INDEX IF NOT EXISTS idx_ai_analysis_email ON ai_analysis(email_id);
CREATE INDEX IF NOT EXISTS idx_ai_analysis_classification ON ai_analysis(classification);

ALTER TABLE ai_analysis ENABLE ROW LEVEL SECURITY;

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
