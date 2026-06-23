-- Persist the full DesignResult JSON on each run so a past design can be re-opened
-- ON-SCREEN (the generated design page), not only downloaded as a PDF.
--
-- Nullable + additive: runs created before this column simply have no on-screen view
-- (their PDF still downloads). RLS already scopes `runs` per firm (Task 5.4), so this
-- inherits the same isolation. No engineering values live here — it is the kernel's own
-- output, rendered read-only.

alter table public.runs
  add column if not exists result jsonb;

comment on column public.runs.result is
  'Full DesignResult JSON (kernel output) for on-screen rendering of a past run. Nullable for legacy runs.';
