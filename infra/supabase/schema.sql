-- Updated DB schema (complete). Paste into your local project or run in Supabase SQL editor.
-- Adds AI columns to authentication.gmail_messages and recreates public view to include them.
-- Adds helper table gmail_messages_ai (non-destructive) and keeps other tables intact.

-- Ensure extension for UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create authentication schema if missing
CREATE SCHEMA IF NOT EXISTS authentication;

-- Stores a single Gmail connection per user plus baseline metadata.
CREATE TABLE IF NOT EXISTS authentication.gmail_connections (
  user_id text PRIMARY KEY,
  gmail_user varchar(255) NOT NULL,
  email varchar(255),
  baseline_at timestamptz NOT NULL,
  baseline_ready boolean NOT NULL DEFAULT false,
  last_poll_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS gmail_connections_baseline_idx ON authentication.gmail_connections (baseline_at DESC);

-- Real table for Gmail messages (authentication schema)
CREATE TABLE IF NOT EXISTS authentication.gmail_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES authentication.gmail_connections(user_id) ON DELETE CASCADE,
  message_id text NOT NULL,
  thread_id text,
  subject text,
  sender text,
  snippet text,
  preview text,
  status text NOT NULL DEFAULT 'new',
  has_attachments boolean NOT NULL DEFAULT false,
  has_images boolean NOT NULL DEFAULT false,
  has_links boolean NOT NULL DEFAULT false,
  gmail_url text,
  crm_record_url text,
  -- AI columns
  ai_routing_decision jsonb,
  ai_summary text,
  ai_confidence double precision,
  -- HubSpot / CRM metadata (nullable)
  hubspot_object_type text,
  hubspot_contact_id text,
  hubspot_company_id text,
  hubspot_deal_id text,
  hubspot_ticket_id text,
  hubspot_order_id text,
  hubspot_note_id text,
  error text,
  received_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, message_id)
);

CREATE INDEX IF NOT EXISTS gmail_messages_user_status_idx ON authentication.gmail_messages (user_id, status, received_at DESC);
CREATE INDEX IF NOT EXISTS gmail_messages_object_idx ON authentication.gmail_messages (hubspot_object_type);

-- Extend authentication.gmail_messages with Salesforce columns (non-destructive)
ALTER TABLE authentication.gmail_messages 
ADD COLUMN IF NOT EXISTS salesforce_object_type text,
ADD COLUMN IF NOT EXISTS salesforce_contact_id text,
ADD COLUMN IF NOT EXISTS salesforce_account_id text,
ADD COLUMN IF NOT EXISTS salesforce_lead_id text,
ADD COLUMN IF NOT EXISTS salesforce_opportunity_id text,
ADD COLUMN IF NOT EXISTS salesforce_case_id text,
ADD COLUMN IF NOT EXISTS salesforce_campaign_id text,
ADD COLUMN IF NOT EXISTS salesforce_order_id text,
ADD COLUMN IF NOT EXISTS salesforce_task_id text;

CREATE INDEX IF NOT EXISTS gmail_messages_salesforce_obj_idx ON authentication.gmail_messages (salesforce_object_type);

-- Non-destructive helper table to store AI writes (safe pattern if public.gmail_messages is a view)
CREATE TABLE IF NOT EXISTS public.gmail_messages_ai (
  gmail_message_id uuid PRIMARY KEY,
  user_id text,
  message_id text,
  ai_routing_decision jsonb,
  ai_summary text,
  ai_confidence double precision,
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gmail_messages_ai_user_msg ON public.gmail_messages_ai (user_id, message_id);

-- Recreate public view to expose the same columns as authentication.gmail_messages
-- This will fail if public.gmail_messages exists as a table. Drop view first if necessary.
DROP VIEW IF EXISTS public.gmail_messages;
CREATE VIEW public.gmail_messages AS
SELECT
  id,
  user_id,
  message_id,
  thread_id,
  subject,
  sender,
  snippet,
  preview,
  status,
  has_attachments,
  has_images,
  has_links,
  gmail_url,
  crm_record_url,
  ai_routing_decision,
  ai_summary,
  ai_confidence,
  hubspot_object_type,
  hubspot_contact_id,
  hubspot_company_id,
  hubspot_deal_id,
  hubspot_ticket_id,
  hubspot_order_id,
  hubspot_note_id,
  salesforce_object_type,
  salesforce_contact_id,
  salesforce_account_id,
  salesforce_lead_id,
  salesforce_opportunity_id,
  salesforce_case_id,
  salesforce_campaign_id,
  salesforce_order_id,
  salesforce_task_id,
  error,
  received_at,
  created_at,
  updated_at
FROM authentication.gmail_messages;

-- HubSpot metadata per Gmail message (audit table)
CREATE TABLE IF NOT EXISTS public.gmail_message_hubspot_meta (
  gmail_message_id uuid PRIMARY KEY REFERENCES authentication.gmail_messages(id) ON DELETE CASCADE,
  ai_routing_decision jsonb,
  ai_summary text,
  hubspot_object_type text,
  ai_confidence double precision,
  hubspot_contact_id text,
  hubspot_company_id text,
  hubspot_deal_id text,
  hubspot_ticket_id text,
  hubspot_order_id text,
  hubspot_note_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS gmail_message_hubspot_meta_obj_idx ON public.gmail_message_hubspot_meta (hubspot_object_type);

-- Salesforce Integration Schema (parallel to HubSpot)
-- Stores Salesforce OAuth connection per user
CREATE TABLE IF NOT EXISTS public.salesforce_connections (
  user_id text PRIMARY KEY,
  salesforce_user varchar(255) NOT NULL,
  email varchar(255),
  instance_url text NOT NULL,  -- e.g., https://yourinstance.my.salesforce.com
  organization_id text,        -- Salesforce Org ID
  last_sync_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS salesforce_connections_user_idx ON public.salesforce_connections (user_id);

-- Salesforce OAuth tokens use existing public.oauth_connections with provider='salesforce'

-- Salesforce message metadata (parallel to gmail_message_hubspot_meta)
CREATE TABLE IF NOT EXISTS public.gmail_message_salesforce_meta (
  gmail_message_id uuid PRIMARY KEY REFERENCES authentication.gmail_messages(id) ON DELETE CASCADE,
  ai_routing_decision jsonb,              -- AI's routing decision for Salesforce
  ai_summary text,
  salesforce_object_type text,            -- Contact, Account, Opportunity, Case, Order
  ai_confidence double precision,
  salesforce_contact_id text,             -- Contact ID in Salesforce
  salesforce_account_id text,             -- Account ID (company/organization)
  salesforce_lead_id text,                -- Lead ID (prospective customer)
  salesforce_opportunity_id text,         -- Opportunity ID (deal in progress)
  salesforce_case_id text,                -- Case ID (support ticket)
  salesforce_campaign_id text,            -- Campaign ID (marketing initiative)
  salesforce_order_id text,               -- Order ID (purchase order)
  salesforce_task_id text,                -- Task ID (note/activity)
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS gmail_message_salesforce_meta_obj_idx ON public.gmail_message_salesforce_meta (salesforce_object_type);
CREATE INDEX IF NOT EXISTS gmail_message_salesforce_meta_gmail_idx ON public.gmail_message_salesforce_meta (gmail_message_id);

-- Helper function to track dual CRM routing
CREATE OR REPLACE FUNCTION public.get_message_crm_status(msg_id uuid)
RETURNS jsonb AS $$
DECLARE
  result jsonb;
BEGIN
  SELECT jsonb_build_object(
    'hubspot_connected', hubspot_object_type IS NOT NULL,
    'salesforce_connected', salesforce_object_type IS NOT NULL,
    'hubspot_objects', jsonb_build_object(
      'type', hubspot_object_type,
      'contact_id', hubspot_contact_id,
      'company_id', hubspot_company_id,
      'deal_id', hubspot_deal_id,
      'ticket_id', hubspot_ticket_id,
      'order_id', hubspot_order_id
    ),
    'salesforce_objects', jsonb_build_object(
      'type', salesforce_object_type,
      'contact_id', salesforce_contact_id,
      'account_id', salesforce_account_id,
      'lead_id', salesforce_lead_id,
      'opportunity_id', salesforce_opportunity_id,
      'case_id', salesforce_case_id,
      'campaign_id', salesforce_campaign_id,
      'order_id', salesforce_order_id
    )
  ) INTO result
  FROM authentication.gmail_messages
  WHERE id = msg_id;

  RETURN COALESCE(result, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql;

-- OAuth connection store keyed by Supabase user id + provider (gmail, hubspot, etc.).
CREATE TABLE IF NOT EXISTS public.oauth_connections (
  user_id text NOT NULL,
  provider text NOT NULL,
  access_token text,
  refresh_token text,
  expires_at timestamptz,
  scope text[],
  email text,
  external_user_id text,
  metadata jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, provider)
);

CREATE INDEX IF NOT EXISTS oauth_connections_provider_idx ON public.oauth_connections (provider);

-- ================================================================
-- GOOGLE SHEETS INTEGRATION
-- ================================================================

-- Create workspaces table (if not exists)
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

-- Enable RLS for workspaces
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own workspaces" ON workspaces FOR SELECT USING (owner_id = auth.uid());
CREATE POLICY "Users can create their own workspaces" ON workspaces FOR INSERT WITH CHECK (owner_id = auth.uid());
CREATE POLICY "Users can update their own workspaces" ON workspaces FOR UPDATE USING (owner_id = auth.uid());
CREATE POLICY "Users can delete their own workspaces" ON workspaces FOR DELETE USING (owner_id = auth.uid());

-- Create emails table (if not exists)
CREATE TABLE IF NOT EXISTS emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    message_id TEXT NOT NULL UNIQUE,
    thread_id TEXT,
    subject TEXT,
    sender_email TEXT,
    sender_name TEXT,
    recipients JSONB DEFAULT '[]'::jsonb,
    body_text TEXT,
    body_html TEXT,
    snippet TEXT,
    received_at TIMESTAMP WITH TIME ZONE,
    has_attachments BOOLEAN DEFAULT FALSE,
    labels TEXT[] DEFAULT '{}',
    processing_status TEXT DEFAULT 'new' CHECK (processing_status IN ('new', 'processing', 'processed', 'error')),
    synced_to_salesforce BOOLEAN DEFAULT FALSE,
    synced_to_hubspot BOOLEAN DEFAULT FALSE,
    synced_to_gsheets BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_emails_workspace ON emails(workspace_id);
CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails(message_id);
CREATE INDEX IF NOT EXISTS idx_emails_gsheet_sync ON emails(synced_to_gsheets);

ALTER TABLE emails ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their workspace emails" ON emails FOR SELECT USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));
CREATE POLICY "Users can insert emails in their workspace" ON emails FOR INSERT WITH CHECK (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));
CREATE POLICY "Users can update their workspace emails" ON emails FOR UPDATE USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));

-- Create ai_analysis table (if not exists)
CREATE TABLE IF NOT EXISTS ai_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    classification TEXT CHECK (classification IN ('Lead', 'Case', 'Contact', 'Opportunity', 'None')),
    confidence_score NUMERIC(3, 2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    urgency TEXT CHECK (urgency IN ('Low', 'Medium', 'High', 'Critical')),
    sentiment TEXT CHECK (sentiment IN ('Positive', 'Neutral', 'Negative')),
    intent TEXT,
    entities JSONB DEFAULT '[]'::jsonb,
    reasoning TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_email_analysis UNIQUE(email_id)
);

CREATE INDEX IF NOT EXISTS idx_ai_analysis_email ON ai_analysis(email_id);
ALTER TABLE ai_analysis ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view AI analysis for their emails" ON ai_analysis FOR SELECT USING (email_id IN (SELECT id FROM emails WHERE workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid())));
CREATE POLICY "Users can insert AI analysis for their emails" ON ai_analysis FOR INSERT WITH CHECK (email_id IN (SELECT id FROM emails WHERE workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid())));

-- Create google_sheets_connections table
CREATE TABLE IF NOT EXISTS google_sheets_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scopes TEXT[],
    spreadsheet_id TEXT NOT NULL,
    spreadsheet_name TEXT,
    spreadsheet_url TEXT,
    sync_mode TEXT DEFAULT 'manual' CHECK (sync_mode IN ('manual', 'automatic')),
    target_sheet_name TEXT DEFAULT 'Emails',
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expired', 'error', 'disconnected')),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_workspace_sheet UNIQUE(workspace_id, spreadsheet_id)
);

CREATE INDEX IF NOT EXISTS idx_gsheets_workspace ON google_sheets_connections(workspace_id);
ALTER TABLE google_sheets_connections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their workspace Google Sheets connections" ON google_sheets_connections FOR SELECT USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));
CREATE POLICY "Users can insert Google Sheets connections for their workspace" ON google_sheets_connections FOR INSERT WITH CHECK (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));
CREATE POLICY "Users can update their workspace Google Sheets connections" ON google_sheets_connections FOR UPDATE USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));
CREATE POLICY "Users can delete their workspace Google Sheets connections" ON google_sheets_connections FOR DELETE USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));

-- Create google_sheets_sync_log table
CREATE TABLE IF NOT EXISTS google_sheets_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES google_sheets_connections(id) ON DELETE CASCADE,
    -- email_id now references authentication.gmail_messages to match Sheets sync source
    email_id UUID NOT NULL REFERENCES authentication.gmail_messages(id) ON DELETE CASCADE,
    sheet_row_number INTEGER,
    sync_status TEXT DEFAULT 'pending' CHECK (sync_status IN ('pending', 'success', 'failed', 'retrying')),
    error_message TEXT,
    classification_type TEXT CHECK (classification_type IN ('Lead', 'Case', 'Contact', 'Opportunity', 'Campaign', 'Deal', 'Order', 'Payment', 'Invoice', 'Quote', 'Task', 'Other')),
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_email_connection UNIQUE(connection_id, email_id)
);

CREATE INDEX IF NOT EXISTS idx_gsheets_log_email ON google_sheets_sync_log(email_id);
ALTER TABLE google_sheets_sync_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their workspace Google Sheets sync logs" ON google_sheets_sync_log FOR SELECT USING (connection_id IN (SELECT id FROM google_sheets_connections WHERE workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid())));
CREATE POLICY "Users can insert sync logs for their workspace" ON google_sheets_sync_log FOR INSERT WITH CHECK (connection_id IN (SELECT id FROM google_sheets_connections WHERE workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid())));

-- Triggers for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_workspaces_updated_at ON workspaces;
CREATE TRIGGER trigger_workspaces_updated_at BEFORE UPDATE ON workspaces FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_emails_updated_at ON emails;
CREATE TRIGGER trigger_emails_updated_at BEFORE UPDATE ON emails FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_gsheets_connections_updated_at ON google_sheets_connections;
CREATE TRIGGER trigger_gsheets_connections_updated_at BEFORE UPDATE ON google_sheets_connections FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- FINAL NOTES:
-- 1) This SQL establishes authentication.gmail_messages as the source-of-truth table,
--    exposes its columns via a public view (public.gmail_messages), and provides a
--    safe helper table public.gmail_messages_ai for upserts by your pipeline if you prefer.
-- 2) After running this, restart your backend and ensure the pipeline writes match the chosen target:
--    - If you want pipeline to write directly into authentication.gmail_messages (preferred), upsert there.
--    - If you want pipeline to write into public.gmail_messages_ai, upsert there instead and keep using LEFT JOINs.
-- 3) Example upsert (backend) for authentication.gmail_messages (PG/psycopg2 or pg client):
--    INSERT INTO authentication.gmail_messages (id, user_id, message_id, ai_routing_decision, ai_summary, ai_confidence, updated_at)
--    VALUES ($1,$2,$3,$4,$5,$6,now())
--    ON CONFLICT (id) DO UPDATE SET ai_routing_decision = EXCLUDED.ai_routing_decision, ai_summary = EXCLUDED.ai_summary, ai_confidence = EXCLUDED.ai_confidence, updated_at = now();
