# Kastra Operations Runbook

Production topology: **Vercel** (React SPA) → **Render** (FastAPI, `render.yaml`) → **Neon** (Postgres).
Email via SendGrid, SMS via Africa's Talking, payments via M-Pesa Daraja + Paystack,
photos on Cloudinary, errors in Sentry.

## Backups & restore

### What protects the database today
- **Neon point-in-time restore (PITR):** Neon retains a WAL history window
  (free tier ≈ 24h, paid plans up to 30 days — check Project → Settings →
  Storage). Any instant inside the window can be restored.
- **Branch-based restore:** restores in Neon create a new branch from a
  timestamp; you then point the app at it. Nothing is overwritten, so a
  restore is itself reversible.

### Weekly off-site dump (do this — PITR alone is not a backup strategy)
PITR disappears if the Neon project is deleted or the account is compromised.
Keep independent dumps:

```bash
# from any machine with pg_dump 16+ (DATABASE_URL from Render/Neon dashboard)
pg_dump "$DATABASE_URL" --format=custom --no-owner \
  --file="kastra-$(date +%F).dump"
```

Store dumps in a private bucket (Cloudflare R2 / Backblaze B2 / S3) — never in
the repo or in GitHub artifacts. Suggested cadence: weekly full dump, retained
for 8 weeks. Automate with a cron job on any trusted machine, or a scheduled
GitHub Action **only** in a private repo with the URL in an Actions secret and
the dump pushed straight to the bucket (never as a workflow artifact).

### Restore procedure (practise this once before you need it)
1. **Stop writes:** Render dashboard → kastra-api → Suspend (prevents the app
   writing to a database you're about to replace).
2. **Neon PITR path:** Neon console → Branches → Restore → pick timestamp →
   creates branch. Copy its connection string.
3. **Dump path:** create an empty database, then
   `pg_restore --no-owner --dbname="$NEW_DATABASE_URL" kastra-YYYY-MM-DD.dump`.
4. Update `DATABASE_URL` on Render (Environment tab), resume the service.
5. Verify: `GET /health`, log in, open an invoice PDF, run one M-Pesa sandbox
   STK push.
6. Post-restore: any payments received during the gap exist in M-Pesa/Paystack
   but not in the DB — reconcile from the Daraja/Paystack dashboards against
   `payment_events`.

## Deploys & rollback

- Backend deploys on push to `main` (Render auto-deploy). Migrations run in the
  build step (`alembic upgrade head`) — write migrations to be
  backward-compatible with the previous code version (add columns nullable,
  never drop/rename in the same release as the code change).
- Rollback: Render → Deploys → "Rollback" to the previous image. This does NOT
  undo migrations; that's why migrations must be backward-compatible.
- Frontend rollback: Vercel → Deployments → promote a previous deployment.

## Scaling beyond one instance

Two things are single-instance-safe by default and need attention first:
1. **Rate limits** — set `REDIS_URL` (e.g. Upstash) so login limits are
   enforced globally instead of per process.
2. **Scheduler** — already guarded by Postgres advisory locks
   (`app/services/scheduler.py`), so multiple instances will not double-send
   reminders or double-credit commissions. No action needed.

## Secret rotation

All secrets live in Render env vars (backend) and Vercel env vars (frontend).
Rotation order that avoids downtime:
1. Add/rotate the secret at the provider (SendGrid, Paystack, Daraja, ...).
2. Update the Render env var — Render redeploys automatically.
3. `SECRET_KEY`/`REFRESH_SECRET_KEY` rotation logs every user out (tokens
   become invalid). Announce it; do it during low-traffic hours.
4. `FIELD_ENCRYPTION_KEY` must NEVER be rotated casually — data encrypted with
   the old key becomes unreadable. Re-encryption requires a migration script.

## Incident triage

- **API down:** Render dashboard → Logs. Every request has an `X-Request-ID`;
  logs are JSON lines keyed by `request_id` — grep the ID a user reports.
- **Payments not landing:** check `payment_events` table, then the Daraja
  callback logs (`/api/mpesa/callback`) and Safaricom dashboard. Callbacks are
  idempotent — replaying is safe.
- **Email not sending:** SendGrid activity feed; the app logs (not raises) on
  send failure.
- **Error spike:** Sentry issue stream (release-tagged).

## Environments

There is currently one environment (production) plus local dev. Before any
risky migration, test it against a Neon branch: create branch → run
`alembic upgrade head` against it → inspect → delete branch.
