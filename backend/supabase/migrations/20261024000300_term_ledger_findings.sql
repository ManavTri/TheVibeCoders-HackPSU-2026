alter table public.findings
  add column if not exists details jsonb;
