-- Enable pgcrypto for UUID generation (safe to run multiple times).
create extension if not exists "pgcrypto";

-- Stores a single Gmail connection per user plus the baseline metadata that
-- gates ingestion. (Baseline ensures we only read email received after connect.)
create table if not exists gmail_connections (
  user_id text primary key,
  gmail_user varchar(255) not null,
  email varchar(255),
  baseline_at timestamptz not null,
  baseline_ready boolean not null default false,
  last_poll_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists gmail_connections_baseline_idx on gmail_connections (baseline_at desc);

-- Lightweight cache of the newest Gmail messages per user. We only keep
-- post-baseline messages and trim the oldest rows in application code.
create table if not exists gmail_messages (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references gmail_connections(user_id) on delete cascade,
  message_id text not null,
  thread_id text,
  subject text,
  sender text,
  snippet text,
  preview text,
  status text not null default 'new',
  has_attachments boolean not null default false,
  has_images boolean not null default false,
  has_links boolean not null default false,
  gmail_url text,
  crm_record_url text,
  error text,
  received_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, message_id)
);

create index if not exists gmail_messages_user_status_idx on gmail_messages (user_id, status, received_at desc);

-- OAuth connection store keyed by Supabase user id + provider (gmail, hubspot, etc.).
create table if not exists oauth_connections (
  user_id text not null,
  provider text not null,
  access_token text,
  refresh_token text,
  expires_at timestamptz,
  scope text[],
  email text,
  external_user_id text,
  metadata jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, provider)
);

create index if not exists oauth_connections_provider_idx on oauth_connections (provider);
