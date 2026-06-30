-- Project-level document/cover metadata, so every calc package generated for a project
-- inherits the same client / project number / site address / responsible engineer / revision
-- without re-typing it per run. Additive + nullable; RLS already scopes projects per firm
-- (Task 5.4) and allows firm-member updates. This is document/admin data, NOT engineering data.

alter table public.projects
  add column if not exists report_metadata jsonb;

comment on column public.projects.report_metadata is
  'Optional document/cover metadata (project_name, client, project_number, site_address, engineer_name, engineer_reg_no, revision) baked into calc packages for this project. Not engineering data.';
