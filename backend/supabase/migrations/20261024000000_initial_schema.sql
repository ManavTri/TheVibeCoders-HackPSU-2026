create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  name text,
  university text,
  created_at timestamptz not null default now()
);

insert into public.profiles (id, name)
select
  users.id,
  coalesce(users.raw_user_meta_data ->> 'name', users.raw_user_meta_data ->> 'full_name')
from auth.users as users
on conflict (id) do nothing;

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  type text not null check (type in ('award_letter', 'tuition_bill', 'study_abroad_quote')),
  filename text not null,
  storage_path text not null unique,
  status text not null default 'uploaded' check (status in ('uploaded', 'extracted', 'failed')),
  extracted_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists documents_user_created_idx
  on public.documents (user_id, created_at desc);

create table if not exists public.validation_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  created_at timestamptz not null default now(),
  document_ids uuid[] not null
);

create index if not exists validation_runs_user_created_idx
  on public.validation_runs (user_id, created_at desc);

create table if not exists public.findings (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.validation_runs (id) on delete cascade,
  rule_id text not null,
  severity text not null check (severity in ('error', 'warning', 'info')),
  title text not null,
  explanation text not null,
  document_ids uuid[] not null,
  fields jsonb not null default '{}'::jsonb,
  suggested_action text not null,
  created_at timestamptz not null default now()
);

create index if not exists findings_run_idx on public.findings (run_id);

alter table public.profiles enable row level security;
alter table public.documents enable row level security;
alter table public.validation_runs enable row level security;
alter table public.findings enable row level security;

create policy "Users can read their own profile"
  on public.profiles for select to authenticated
  using (id = (select auth.uid()));
create policy "Users can update their own profile"
  on public.profiles for update to authenticated
  using (id = (select auth.uid())) with check (id = (select auth.uid()));
create policy "Users can read their own documents"
  on public.documents for select to authenticated
  using (user_id = (select auth.uid()));
create policy "Users can read their own validation runs"
  on public.validation_runs for select to authenticated
  using (user_id = (select auth.uid()));
create policy "Users can read findings from their own runs"
  on public.findings for select to authenticated
  using (
    exists (
      select 1 from public.validation_runs run
      where run.id = findings.run_id and run.user_id = (select auth.uid())
    )
  );

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('student-documents', 'student-documents', false, 10485760, array['application/pdf'])
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

create policy "Users can read their own stored documents"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'student-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );
create policy "Users can upload their own stored documents"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'student-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );
create policy "Users can delete their own stored documents"
  on storage.objects for delete to authenticated
  using (
    bucket_id = 'student-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

create or replace function public.create_profile_for_new_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.profiles (id, name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'name', new.raw_user_meta_data ->> 'full_name'));
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.create_profile_for_new_user();
