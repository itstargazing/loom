# LOOM production deploy

This runbook covers a public soft launch and Global GA ops. Local development still uses the root `docker-compose.yml`.

## Architecture

| Piece | Recommended host |
|-------|------------------|
| Dashboard (Next.js) | Vercel, or the `dashboard` service in `docker-compose.prod.yml` |
| API + worker | `docker-compose.prod.yml` (or the same images on Render/Fly) |
| Postgres + Redis | Compose volumes, or managed Postgres/Redis with matching `DATABASE_URL` / `REDIS_URL` |

## Soft-launch checklist

1. Create a Clerk application. Copy the JWKS URL and issuer into `JWT_JWKS_URL` / `JWT_ISSUER`.
2. Set `AUTH_MODE=jwt`, `ENVIRONMENT=production`. Stub auth and stub AI refuse to start.
3. Set a real `AI_PROVIDER` + key and `EMBEDDING_PROVIDER` + key.
4. Set `CORS_ORIGINS` to the exact dashboard origin (e.g. `https://app.example.com`).
5. Dashboard: `LOOM_API_URL` (server-side), Clerk publishable + secret keys. Do **not** set `LOOM_API_TOKEN` in production.
6. Optional but recommended: `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN`.
7. Extension store/build: bake `VITE_LOOM_API_BASE_URL` and `VITE_LOOM_DASHBOARD_ORIGIN` (see `docs/chrome-web-store.md`).

## Compose

```bash
# From repo root, with required vars in the environment or a root .env
docker compose -f docker-compose.prod.yml up -d --build
curl -fsS http://localhost:8000/ready
```

`/health` is liveness only. `/ready` returns 503 until Postgres and Redis respond.

## Vercel dashboard

Env vars:

- `LOOM_API_URL` — public HTTPS API base (not `http://backend:8000` unless using a tunnel)
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`
- Sign-in/up URLs as in `.env.example`
- Optional `CLERK_JWT_TEMPLATE` if you use a custom Clerk JWT template that the API expects

Point `CORS_ORIGINS` on the API at the Vercel deployment URL.

## Clerk JWT

The API accepts Clerk session JWTs via JWKS. Keep issuer aligned with the Clerk Frontend API host. Audience is optional unless you configure a template that sets `aud`.

## Billing (GA)

Set `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PRO`, and success/cancel URLs. Webhook path: `POST /api/billing/webhook`.

## Retention

- `CAPTURE_RETENTION_DAYS` (default 365)
- `SKILL_RETENTION_DAYS` (default 365)

The worker periodically deletes older rows. Account delete (`DELETE /api/auth/me`) and export (`GET /api/auth/me/export`) remain available.

## Backups

- Snapshot Postgres regularly (`pg_dump` or provider backups).
- Persist the `form_data` volume (uploaded PDFs under `FORM_STORAGE_DIR`).
- Redis AOF is enabled in prod compose; treat Redis as ephemeral for queues/rate limits, not primary truth.

## Monitoring

- Probe `/ready` from your uptime checker.
- Enable Sentry in production (`SENTRY_TRACES_SAMPLE_RATE` default 0.1 in compose).
- Watch worker logs for stream backlog and classification failures.
