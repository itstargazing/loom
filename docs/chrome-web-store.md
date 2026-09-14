# Chrome Web Store packaging

## Build for store / production

```bash
cd extension
# Optional bake-ins for a hosted deploy:
#   VITE_LOOM_API_BASE_URL=https://api.example.com
#   VITE_LOOM_DASHBOARD_ORIGIN=https://app.example.com
npm run build
```

Upload the contents of `extension/dist` as an unpacked package or zip for the store.

Version lives in `extension/manifest.json` (currently 0.2.0 for GA packaging).

## Permissions justification (draft)

| Permission | Why |
|------------|-----|
| `storage` | Queue, sync config, privacy settings |
| `tabs` / `activeTab` | Page title/URL for capture context |
| `webNavigation` | Page-open signals |
| `downloads` | Form-filler PDF download |
| `alarms` / `idle` | Sync backoff and idle-friendly flush |
| Host `<all_urls>` | Ambient capture on pages the user browses |
| `file:///*` | Local PDF viewer / form fill |

Trim host permissions only if you drop ambient capture or PDF file support.

## Privacy practices form (checklist)

- [ ] Single purpose: capture browsing signals into the user's LOOM account
- [ ] Data used: page URLs, titles, selected text, dwell, PDF text (user-configurable)
- [ ] Data shared with: LOOM backend (operator-hosted); Clerk for auth; Stripe for billing; AI provider for classification/Ask
- [ ] Not sold
- [ ] Remote code: no
- [ ] Link Privacy Policy: `https://<dashboard>/legal/privacy`

## Onboarding without token paste

1. User installs extension and opens Options (API URL pre-filled for store builds).
2. User signs in on the dashboard.
3. User clicks **Sync now** — dashboard passes Clerk JWT through the bridge for that run.
4. Optional: paste a long-lived token in Options for background sync when the dashboard is closed.
5. Hosted dashboards: add the origin under Extra dashboard origins (pre-seeded when `VITE_LOOM_DASHBOARD_ORIGIN` is set).

## Review tips

- Screenshots: overview, Sync now, Local-only domains clarifying cloud sync, Ask with citations.
- Do not claim “data never leaves the device.”
- Provide a test account for reviewers if the API is gated.
