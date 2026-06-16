# TorenOne — Report-PDF retention & lifecycle (§6.2)

> Calc-package PDFs in the private `reports` Storage bucket (and their `reports` /
> `runs` rows) accumulate forever today. This is the retention policy and the tool that
> enforces it.

## Policy

- **Default retention: 365 days.** A report PDF is kept for at least one year from the
  run that produced it, then becomes eligible for deletion. Tune per the firm's
  contract / PoPIA obligations (see §2.3) via `REPORT_RETENTION_DAYS`.
- **Engineer's record is separate.** TorenOne stores the *computational* artefact; the
  authoritative stamped record lives in the firm's own document system. Retention here
  is about not hoarding storage indefinitely, not about being the system of record.
- **Storage object first, DB row second.** Deletion removes the Storage object before
  the `reports` row, so a row never points at a missing object and a partial run is
  safely re-runnable (idempotent).

## Enforcement — `tools/prune_reports.py`

A standalone pruner (no service dependency) finds reports whose owning run is older than
the retention window, deletes the Storage object via the Storage REST API
(service-role), then deletes the `reports` row.

```bash
# Dry-run (default): list what WOULD be deleted, change nothing.
SUPABASE_DB_URL=... SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
  python tools/prune_reports.py --days 365

# Apply: actually delete.
SUPABASE_DB_URL=... SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
  python tools/prune_reports.py --days 365 --apply
```

- `--days` defaults to `REPORT_RETENTION_DAYS` (or 365).
- Without `--apply` it is a **dry run** — it prints the candidates and exits 0.
- It is **idempotent**: re-running after a partial failure simply re-deletes whatever
  remains. It uses the same injected-seam design as `SupabaseReportStore`, and its core
  logic is unit-tested in `service/tests/test_prune_reports.py` (no live project).

> The `SUPABASE_DB_URL` should point at the same transaction pooler used by the service
> (see `docs/DB_OPS.md`). The pruner opens one connection and closes it.

## Scheduling

Run it monthly. Any of:

- **Cron on a small box / the Fly machine:**
  `0 3 1 * * cd /app && python tools/prune_reports.py --apply`
- **A GitHub Actions cron** (`schedule:` + `workflow_dispatch`) with the three secrets,
  gated like the E2E job — start with `--dry-run` for a cycle, read the output, then add
  `--apply`.
- **A Supabase scheduled task / pg_cron** triggering the same logic — note that
  deleting a `storage.objects` row in SQL does **not** delete the underlying file, which
  is exactly why the pruner goes through the Storage REST API.

## Rollout

1. Ship with the **dry-run scheduled** for a cycle; eyeball what it would remove.
2. Confirm nothing surprising (e.g. a firm that needs > 1 year), adjust
   `REPORT_RETENTION_DAYS` if needed.
3. Flip to `--apply`.

Deferred (founder/§6.1): a Storage bucket-level lifecycle rule and PITR policy are
infra settings in the Supabase dashboard; this app-level pruner is the deterministic,
testable enforcement we control.
