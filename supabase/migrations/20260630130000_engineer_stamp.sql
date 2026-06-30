-- Engineer review & e-stamp (T1-1).
--
-- A registered-engineer capability, granted per person by the firm owner, plus a stamp
-- recorded on a design run. Additive + nullable; RLS already scopes profiles/runs per firm.
-- The stamp records that a named, ECSA-registered engineer accepted professional
-- responsibility — it is NOT a claim that TorenOne validated anything.

-- Per-person registered-engineer capability (only such users may apply an e-stamp).
alter table public.profiles
  add column if not exists is_registered_engineer boolean not null default false,
  add column if not exists ecsa_reg_no text;

comment on column public.profiles.is_registered_engineer is
  'True if the firm owner has marked this person a registered (ECSA) engineer permitted to e-stamp calc packages.';

comment on column public.profiles.ecsa_reg_no is
  'The person''s ECSA registration number, shown on calc packages they stamp.';

-- The e-stamp applied to a design run (null = not stamped). Holds engineer_name, ecsa_reg_no,
-- stamped_at (ISO-8601 UTC), stamped_by (profile id) and fingerprint (report fingerprint at
-- stamp time, for tamper-evidence).
alter table public.runs
  add column if not exists stamp jsonb;

comment on column public.runs.stamp is
  'Registered-engineer e-stamp for this run (null = unstamped): engineer_name, ecsa_reg_no, stamped_at, stamped_by, fingerprint.';
