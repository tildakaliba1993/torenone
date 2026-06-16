# TorenOne — Database connection & pool sizing (§6.3)

> How the engineering service talks to Postgres, and how we keep `/design` runs from
> exhausting connections under concurrency.

## The connection model

The service does **not** hold a long-lived in-process connection pool. The
Supabase-backed `ReportStore` (`service/src/torenone_service/reports.py`) opens **one
short-lived `psycopg` connection per `/design` request**, does its `runs` + `reports`
writes in a single transaction, and **closes it** in a `finally`. `/parse` and
`/health` touch no database at all.

Consequences:

- **Peak DB connections ≈ peak concurrent `/design` requests** — there is no pool that
  can leak or sit idle holding backends open.
- The connection acquire is **bounded**: `connect_timeout` (env
  `SUPABASE_DB_CONNECT_TIMEOUT_S`, default **10 s**). If the pooler is saturated the
  request fails fast as a 502 instead of hanging a worker.
- Every connection is tagged `application_name=torenone-service` (env
  `SUPABASE_DB_APPLICATION_NAME`) so it's identifiable in `pg_stat_activity` and the
  Supabase dashboard.

## Sizing — keeping under the limit

Two limits compound. We bound the **left** side (the service's concurrency) so it stays
well under the **right** side (Postgres/pooler capacity):

```
peak DB connections  ≈  (Fly machines) × (per-machine request hard_limit)
```

- **Per-machine concurrency is capped at the edge** in `fly.toml`
  (`[http_service.concurrency] hard_limit = 8`). So one machine opens **≤ 8**
  concurrent DB connections; ten machines ≤ 80.
- **Use the Supabase transaction pooler** for `SUPABASE_DB_URL` in production — the
  pooler host on **port 6543** (Supabase dashboard → Database → Connection string →
  *Transaction* mode), **not** the direct `db.<ref>.supabase.co:5432` host. Transaction
  pooling multiplexes many short-lived client connections onto a small set of Postgres
  backends, which is exactly our connect-per-request pattern.
- Direct-Postgres `max_connections` on Supabase's smaller tiers is ~60; the transaction
  pooler comfortably absorbs our capped concurrency below that.

### If we outgrow this

- Lower `hard_limit` / add machines to trade latency for connection headroom, or move
  to a larger Supabase compute tier (higher `max_connections`).
- Only then consider an in-process `psycopg_pool.ConnectionPool` (bounded `max_size`)
  opened at app startup — deferred now because connect-per-request + the transaction
  pooler is simpler and already bounded. The `connect` callable in `SupabaseReportStore`
  is the single seam where a pool would slot in.

## Load-test before the pilot (ties to §4.5)

Before opening the pilot, drive a handful of concurrent `/design` runs (≥ `hard_limit`)
and confirm:

- no `too many connections` / `remaining connection slots` errors in the logs;
- each design still completes within the 60 s NFR (NFR-5);
- `pg_stat_activity` (filter `application_name = 'torenone-service'`) drains back to ~0
  shortly after the burst — i.e. connections are released, not leaked.

## Relevant env vars

| Variable | Default | Purpose |
|---|---|---|
| `SUPABASE_DB_URL` | — | Postgres connection string — **transaction pooler (6543)** in prod |
| `SUPABASE_DB_CONNECT_TIMEOUT_S` | `10` | Max wait to acquire a connection (fast-fail) |
| `SUPABASE_DB_APPLICATION_NAME` | `torenone-service` | Tag in `pg_stat_activity` |

When `SUPABASE_DB_URL` (or `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`) is unset the
service falls back to the in-memory store (local/dev/tests) and opens no connections.
