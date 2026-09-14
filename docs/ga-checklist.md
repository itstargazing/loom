# Global GA exit checklist

Use with `docs/production.md` and `docs/chrome-web-store.md`.

## Soft public launch (B2C)

- [ ] `docker compose -f docker-compose.prod.yml` (or equivalent) with `AUTH_MODE=jwt`, real AI/embeddings
- [ ] Dashboard on Vercel or prod Compose with Clerk keys; `LOOM_API_URL` public
- [ ] `/ready` monitored; Sentry DSN set in production
- [ ] CI green on main (`.github/workflows/ci.yml`)
- [ ] `/legal/privacy` and `/legal/terms` linked from marketing footer and Account
- [ ] Account export + delete verified
- [ ] Retention days configured; worker includes retention purge
- [ ] Extension build with production API/dashboard origins; Sync now works signed-in
- [ ] Local-only copy does not claim on-device-only storage

## Global GA

- [ ] Redis rate limits active for capture, classify, Ask
- [ ] Free-tier quotas enforced; Pro via Stripe Checkout + webhook
- [ ] Clerk Organizations enabled (seats/membership); personal data model documented
- [ ] Extension on Chrome Web Store (or approved unlisted) with privacy practices form
- [ ] Counsel review of Privacy/Terms for target markets
- [ ] Postgres backups + form PDF volume strategy
- [ ] Load smoke: capture → classify → Ask under a real Clerk user

## Honest data model note

Team billing uses Clerk Organizations. Capture events and skill stores remain scoped to personal `user_id` until an explicit org-shared store ships.
