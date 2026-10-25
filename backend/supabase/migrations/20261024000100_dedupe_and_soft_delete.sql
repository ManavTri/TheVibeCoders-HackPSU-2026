alter table public.documents
  add column content_sha256 text,
  add column archived_at timestamptz,
  add column deleted_at timestamptz;

create unique index documents_user_content_sha256_unique
  on public.documents (user_id, content_sha256)
  where content_sha256 is not null;
