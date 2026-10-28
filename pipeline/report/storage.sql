-- Weekly issues (PDF, charts, issue.json) live in the private Storage bucket "reports".
-- Signed-in readers on public.readers can download them; nobody else can list or read them.
-- Uploads use the project's secret key (service role), which bypasses RLS, so there is no
-- insert/update/delete policy. Applied idempotently by `python -m pipeline.report publish`.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('reports', 'reports', false, 20971520, array['application/pdf', 'image/png', 'application/json'])
on conflict (id) do update
  set public = false,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists reports_readers_only on storage.objects;
create policy reports_readers_only on storage.objects for select to authenticated
  using (bucket_id = 'reports' and (select private.is_reader()));
