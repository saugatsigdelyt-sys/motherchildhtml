-- ============================================================
-- WhatsApp Business Onboarding — Supabase Setup
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- Drop table if re-running (safe to remove this line in production)
drop table if exists whatsapp_accounts;

-- Main table: one row per onboarded WhatsApp Business Account
create table whatsapp_accounts (
  id                uuid        default gen_random_uuid() primary key,
  app_id            text        not null,
  app_secret        text        not null,
  config_id         text,
  waba_id           text        not null,
  phone_number_id   text        not null,
  business_id       text,
  access_token      text        not null,
  status            text        not null default 'active',
  created_at        timestamptz not null default now()
);

-- Index for fast lookup by WABA ID (used by webhooks / Cloud API integrations)
create index idx_whatsapp_accounts_waba_id       on whatsapp_accounts (waba_id);
create index idx_whatsapp_accounts_phone_number  on whatsapp_accounts (phone_number_id);

-- ============================================================
-- Row Level Security
-- Service role key (used by your backend) bypasses RLS by
-- default, so these policies only matter if you ever query
-- from the frontend or anon key — keep them locked down.
-- ============================================================
alter table whatsapp_accounts enable row level security;

-- Block all access via anon / public key (backend uses service role)
create policy "No public access"
  on whatsapp_accounts
  for all
  using (false);

-- ============================================================
-- Done. You should now see the table in:
-- Supabase Dashboard → Table Editor → whatsapp_accounts
-- ============================================================
