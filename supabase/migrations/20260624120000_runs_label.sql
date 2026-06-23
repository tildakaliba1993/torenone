-- Optional, user-editable label for a design run, so designs can be named, searched and
-- renamed (project/design management). Nullable + additive; RLS already scopes runs per
-- firm (Task 5.4). When null, the UI shows a derived label (geometry + mode).

alter table public.runs
  add column if not exists label text;

comment on column public.runs.label is
  'User-editable display name for a design run (searchable). Null → UI derives one from the spec.';
