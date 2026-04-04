create table if not exists public.analytics_snapshots (
  snapshot_key text primary key,
  scope_type text not null default 'global',
  scope_id text not null default 'dashboard',
  payload jsonb not null default '{}'::jsonb,
  generated_at timestamptz not null default now()
);

create index if not exists analytics_snapshots_generated_at_idx
  on public.analytics_snapshots (generated_at desc);

create index if not exists analytics_snapshots_payload_gin_idx
  on public.analytics_snapshots using gin (payload);
