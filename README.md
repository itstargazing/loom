# LOOM

LOOM is a browser extension plus backend that ambiently captures signals as you browse and routes them into structured, running documents.

## Architecture

**Capture → Classify → Route** — one shared pipeline with pluggable skills and a dashboard to view everything the pipeline has produced.

## Project Structure

```
loom/
├── extension/          # Chrome extension (Manifest V3, TypeScript, Vite)
├── backend/            # Python FastAPI API (PostgreSQL, Redis)
├── dashboard/          # Next.js 16 App Router dashboard (React 19)
├── shared/
│   ├── design-system/  # Shared tokens, Tailwind preset, CSS components
│   └── bridge/         # Dashboard ↔ extension message contract
└── docker-compose.yml
```

## Design System

LOOM uses a shared design system in `shared/design-system/` consumed by both the dashboard and extension:

- **Tokens** (`tokens.ts`) — colors, typography, spacing, motion
- **Tailwind preset** (`tailwind.preset.ts`) — imported by both Tailwind configs
- **Global CSS** (`globals.css`) — CSS variables and component classes (`.loom-btn`, `.loom-card`, `.loom-overlay`, etc.)

Preview all tokens and components at [http://localhost:3000/style-guide](http://localhost:3000/style-guide) when the dashboard is running.

## Capture Layer

LOOM captures five passive signals with no explicit user action beyond normal browsing. Each is toggleable independently from the extension popup, and toggling takes effect immediately on already-open tabs.

| Signal | Default | What it captures |
|--------|---------|------------------|
| `highlight_selected` | **on** | Text you select, plus the paragraph around it |
| `text_copied` | **on** | Text you copy, plus the paragraph around it |
| `page_opened` | off | Readable text of pages and PDFs you open |
| `scroll_dwell` | off | Which sections of a long page held your attention |
| `upload_field_detected` | off | When a file upload field appears, and its label text |

```
extension/src/capture/
├── types.ts           # Event types, payloads, plain-language descriptions
├── settings.ts        # Per-signal toggles (chrome.storage.sync)
├── emitter.ts         # Batching + debouncing → background service worker
├── dom-utils.ts       # Context, heading, and label extraction
├── dom-watcher.ts     # One shared debounced MutationObserver
├── readable-text.ts   # Reader-mode-style extraction for web pages
├── index.ts           # Installs enabled signals, reacts to settings changes
└── signals/
    ├── highlight.ts
    ├── copy.ts
    ├── page-opened.ts
    ├── scroll-dwell.ts
    └── upload-field.ts
```

### Performance notes

Content scripts run on every page, so the capture layer is built to stay cheap:

- A **disabled signal attaches nothing** — no listeners, no observers.
- Signals that need to see new DOM nodes share **one debounced MutationObserver**, and process batches in `requestIdleCallback`.
- `scroll_dwell` uses an `IntersectionObserver` rather than a scroll listener, and caps tracking at 400 sections per page.
- `page_opened` extraction is deferred to browser idle and works on a detached DOM clone.

### Sync pipeline

Captured events travel from the browser to Postgres through a durable path at every hop:

```
content script ──► service worker ──► POST /api/capture/events ──► Redis stream ──► worker ──► Postgres
   (5s batches)     (chrome.storage       (202 Accepted,            (consumer         (bulk upsert)
                     local queue)          nothing persisted yet)    group)
```

**Extension side.** The service worker appends events to a queue in `chrome.storage.local` — not memory, because an MV3 service worker is terminated whenever it goes idle. Sync runs on arrival, on a `chrome.alarms` tick every minute, and whenever the browser goes idle. Failures back off exponentially with jitter from 5s up to 5 minutes, and the backoff deadline lives in storage so it survives a worker restart.

**Backend side.** The endpoint validates a batch, writes it to a Redis stream, and returns `202` — the extension is never blocked on a database write. A separate worker process consumes the stream with a consumer group, bulk-inserts into `capture_events`, and only then acknowledges. A worker that dies mid-batch leaves its entries pending, and another worker reclaims them via `XAUTOCLAIM`.

Delivery is at-least-once, so event ids are generated client-side and used as the primary key. Replays and redeliveries collapse into a single row via `ON CONFLICT DO NOTHING`.

Two failure modes get explicit handling rather than infinite retries: a batch rejected with a `4xx` (other than 408/429) is dropped with a logged error instead of wedging the queue behind it, and a stream entry that fails validation is acknowledged and dropped rather than redelivered forever.

### Verifying the pipeline

```bash
docker compose up --build          # api, worker, postgres, redis, dashboard
```

The popup shows queued count, total sent, last sync time, and the last error, plus a manual **Sync now** button. To confirm rows landed:

```bash
curl -H "Authorization: Bearer loom-dev-token" \
  http://localhost:8000/api/capture/events?limit=10
```

### Dev debug feed

The popup shows a live feed of captured events in development builds, so capture can be verified before anything downstream exists:

```bash
cd extension
npm run dev    # builds in development mode, which enables the panel
```

The feed reads from an in-memory ring buffer in the service worker. Phase 2.1 stores nothing durable — persistence and backend sync arrive in Phase 2.2.

## Classification Layer

Every persisted event is classified into one or more skill categories. Classification decides *what* an event is; it deliberately writes nothing into typed skill stores yet.

```
Postgres ──► Redis stream ──► classification worker ──► AI client ──► event_classifications
(capture_events) (loom:classify:events)                (strict JSON)          │
                                                                             ▼
                                                                    typed skill stores
```

The capture worker publishes only rows it actually inserted, using `INSERT ... RETURNING`. A redelivered event is therefore never classified twice, which matters because each classification costs a model call.

A classification is marked `routed_at` only after the routing commit, so an event that was classified but crashed before reaching the stores is picked up again on the next pass. The upserts described under [Deduplication](#deduplication) make that replay harmless.

### Categories

| Category | Extracted fields |
|----------|------------------|
| `glossary_term` | term, definition |
| `citation` | quote, author, work title, publisher, published date |
| `deadline` | title, date, kind |
| `contradiction_candidate` | claim, topic |
| `reading_highlight` | passage |
| `product_listing` | name, price, specs |
| `job_listing` | title, company, salary, requirements, deadline |
| `contract_clause` | clause text, flag reason, risk level |
| `none` | — |

One event may match several categories: a highlight inside an academic PDF can be both a `glossary_term` and a `reading_highlight`. `none` must appear alone, and a category may not repeat.

### Structured output

The provider is asked for JSON conforming to a schema generated from the Pydantic models, using OpenAI Structured Outputs (`strict: true`). Output is then re-validated server-side, because schema conformance does not imply usefulness — a `glossary_term` with a null `definition` satisfies the JSON schema but is useless, so per-category required fields are enforced in Python.

On invalid output the classifier retries **once**, showing the model its own response and the exact validation error. A second failure is recorded as a failed row with the raw output kept for debugging. A transport error is not retried inline; the queue entry stays unacknowledged so it is reclaimed later.

Strict mode accepts only a subset of JSON Schema, and Pydantic silently emits unsupported keywords as soon as a model gains a field default, a `Field(ge=...)` constraint, or a discriminated union. `tests/test_classification_schema.py` asserts the generated schema stays compatible, so that breakage surfaces in CI rather than as every classification failing at runtime.

### Providers

`app/ai/` is the only place that knows which provider is configured. Nothing else imports a vendor SDK.

- **`openai`** — any OpenAI-compatible endpoint, over plain HTTP via httpx. Point `AI_BASE_URL` at a gateway to switch backends.
- **`stub`** *(default)* — keyword heuristics, no network, no API key. It exists so the pipeline runs and is testable out of the box; its accuracy is not comparable to a real model, and it returns `none` whenever nothing obvious matches.

With `AI_PROVIDER=openai` and an empty `AI_API_KEY`, LOOM logs a warning and falls back to the stub rather than failing every event.

The prompt lives in `app/prompts/classify_event.py`, separate from pipeline code so it can be iterated on directly.

### Verifying classification

To see what the current prompt and provider produce against sample events — and which store each result would be routed into — with no database or Redis running:

```bash
cd backend
python -m scripts.demo_classify
```

Against a live pipeline:

```bash
curl -H "Authorization: Bearer loom-dev-token" \
  http://localhost:8000/api/classifications/stats

curl -H "Authorization: Bearer loom-dev-token" \
  "http://localhost:8000/api/classifications?only_failed=true"
```

To re-run the classifier on one event after editing the prompt, bypassing the queue:

```bash
curl -X POST -H "Authorization: Bearer loom-dev-token" \
  http://localhost:8000/api/classifications/<capture_event_id>/reclassify
```

## Skill Stores & Router

Classification decides *what* an event is; the router writes it where the skills read from. This is the last piece of shared infrastructure — every skill from Phase 5 onward is a UI plus skill-specific logic on top of these tables.

| Store | Holds |
|-------|-------|
| `glossary_terms` | term, definition, context snippet |
| `citations` | quote, author, work, publisher, date, formatted strings |
| `deadlines` | title, due text, resolved date, kind |
| `contradiction_claims` | one checkable claim plus its topic |
| `contradictions` | two conflicting claims, written by Phase 8 rather than the router |
| `reading_compiler_entries` | passage, dwell duration, heading |
| `product_listings` | name, price, schemaless specs |
| `job_listings` | title, company, salary, requirements, deadline |
| `contract_flags` | clause text, flag reason, risk level |

A classification produces a single claim, but a contradiction needs two claims from different sources. So `contradiction_claims` is what the router writes, and Phase 8 clusters those by topic and promotes conflicting pairs into `contradictions`.

Every entry keeps `capture_event_id`, so any row traces back to the browsing moment that produced it. That foreign key is `ON DELETE SET NULL` rather than `CASCADE`: purging raw capture history should not silently erase the structured output derived from it.

### Deduplication

Delivery is at-least-once and people revisit pages, so routing has to be idempotent. Each entry carries a `dedup_key` — a hash of the normalised fields that make two captures "the same thing" for that skill — with a unique constraint on `(user_id, dedup_key)`. Writes are upserts: a repeat sighting bumps `times_seen`, appends to the `occurrences` JSONB array, and keeps the highest confidence seen, rather than inserting a duplicate.

What counts as identity differs per skill, and the differences are deliberate:

| Skill | Identity | Why |
|-------|----------|-----|
| Glossary | term | The same term on ten pages is one entry with ten sightings |
| Citations | quote | One passage reached via two URLs is a single citation |
| Deadlines | title + date + source | Two courses can share "Problem Set 3" on one date yet be different obligations |
| Contradiction claims | claim + source | The whole point is spotting one topic claimed differently by different sources |
| Products / Jobs | source + name | A listing page is one item; revisiting updates it |

`collection_id` is deliberately *not* part of identity, both because grouping is not identity and because Postgres treats NULLs as distinct — which would silently defeat dedup for every unfiled entry.

### Adding a skill

Add one entry to `ROUTES` in `app/services/skill_router.py` and one to `SKILL_RESOURCES` in `app/routers/skills.py`. The pipeline itself never changes. Tests assert both registries stay in sync with the models, so a store with no route (silently swallowed data) or no endpoint (invisible to the dashboard) fails the suite.

### Collections

Collections are user-named groupings that entries can be filed under. They are optional everywhere — an entry with no collection is simply unfiled — and deleting one leaves its entries intact and unfiled.

```bash
curl -X POST -H "Authorization: Bearer loom-dev-token" \
  -H "Content-Type: application/json" \
  -d '{"name": "Thesis reading"}' \
  http://localhost:8000/api/collections
```

### Reading the stores

```bash
curl -H "Authorization: Bearer loom-dev-token" http://localhost:8000/api/skills/glossary
curl -H "Authorization: Bearer loom-dev-token" http://localhost:8000/api/overview
```

Slugs are `glossary`, `citations`, `deadlines`, `contradiction-claims`, `reading`, `products`, `jobs`, and `contract-flags`.

## Dashboard

The dashboard is the read side of the pipeline: a sidebar of skills, an overview of what the pipeline has produced, and one page per store.

```
dashboard/src/
├── app/
│   ├── page.tsx                 # Overview
│   ├── skills/[slug]/page.tsx   # One route serving all eight stores
│   └── style-guide/             # Design token reference
├── components/
│   ├── sidebar.tsx              # Skill navigation
│   ├── capture-status.tsx       # Queue state + manual sync (client)
│   ├── activity-feed.tsx        # Cross-skill recent activity
│   └── skill-table.tsx          # Renders any store from its registry entry
└── lib/
    ├── api.ts                   # Server-side backend client
    ├── skills.ts               # Slugs, labels, and column layout per skill
    └── types.ts                 # Mirrors the backend read models
```

### One request per page

`GET /api/overview` returns per-skill counts, recent activity across every store, and pipeline health in a single payload. The recent-activity feed spans eight tables, so the backend projects each onto a shared shape and combines them with `UNION ALL`, letting Postgres do the interleaving and limiting. Adding a skill extends the union automatically via `SKILL_RESOURCES`.

Pages render server-side with `cache: "no-store"`, since the pipeline writes continuously and a cached page would be misleading. When the backend is unreachable, the affected panel says so and names the URL it tried rather than failing the whole page.

### Adding a skill to the dashboard

Add one entry to `SKILL_VIEWS` in `lib/skills.ts` with the slug, label, and the columns specific to that store; the shared envelope columns (source, confidence, times seen, last seen) are appended by `skill-table.tsx`. No new page component is needed for a table view. Skills that outgrow a table (Glossary is the first) get a dedicated page at `app/skills/<slug>/page.tsx`, which Next.js prefers over the dynamic `[slug]` route.

## Glossary

The first fully built skill, on top of the shared pipeline.

**Classification.** The prompt now treats glossary terms as one-to-five-word jargon, not ordinary sentences. The stub classifier (used when no API key is set) takes the same stance: a punctuated sentence is not a term, and the definition is the sentence in the captured context that actually contains the highlight.

**Context, not just the term.** The model extracts `term` + `definition`. The surrounding paragraph from the original highlight is stored as `context_snippet` and appended to `occurrences` on later sightings, which is what the "seen in these contexts" view reads.

**Dashboard.** `/skills/glossary` is an alphabetized, searchable list — not the generic table. Each entry can be edited, deleted, or filed into a named collection. Repeat sightings expand to show every source.

**Extension.** After a highlight is classified as a glossary term, a small auto-dismissing confirmation appears next to the selection. It is rendered in a shadow root so page CSS cannot restyle it, and it never auto-attaches anything: it is feedback, not a prompt.

```bash
curl -H "Authorization: Bearer loom-dev-token" \
  "http://localhost:8000/api/skills/glossary?sort=alpha&q=encoding"
```

## Citations

The second fully built skill. Copy a claim from a paper or article and LOOM files it as a citation with APA and MLA strings generated from the page metadata.

**Classification.** The prompt treats citations as attributable claims — findings, figures, quoted statements — and refuses passwords, code, URLs-alone, and casual chat. The stub classifier (no API key) follows the same rule and pulls author, work title, publisher, and date from the copy, the page title, and the host when they are present.

**Formatted on the way in.** Routing writes `formatted.apa` and `formatted.mla` from those fields. Correcting author, title, publisher, or date on the dashboard rebuilds both strings.

**Dashboard.** `/skills/citations` groups quotes by collection. A style toggle switches APA/MLA, metadata can be corrected by hand, and a collection (or everything) exports as plain text or Markdown.

**Extension.** After a copy is classified as a citation, the same auto-dismissing confirmation used by the glossary appears next to the selection.

```bash
curl -H "Authorization: Bearer loom-dev-token" \
  "http://localhost:8000/api/skills/citations?q=temperature"

curl -H "Authorization: Bearer loom-dev-token" \
  "http://localhost:8000/api/skills/citations/export?style=apa&format=txt" \
  -o bibliography-apa.txt
```

## Deadlines

Dated obligations pulled from pages and PDFs you open, shown on one calendar.

**Classification.** `page_opened` events on syllabi, contracts, and event pages are flagged as deadline-relevant. The model still emits a single deadline (categories cannot repeat); a second pass then extracts every other date-like mention on the page, with a title, kind, confidence, and the surrounding sentence.

**Resolved dates.** Free text such as `2026-09-15` or `October 20, 2026` becomes `due_date`. Unresolvable phrasing (`end of term`) stays as `due_text`. Two versions of the same syllabus merge; two courses that share "Problem Set 3" do not.

**Dashboard.** `/skills/deadlines` is a month/list calendar. Filter by source document. Click an item to see the original sentence. Extractions below 0.5 confidence are marked until you confirm them.

```bash
curl -H "Authorization: Bearer loom-dev-token" \
  http://localhost:8000/api/skills/deadlines

curl -X PATCH -H "Authorization: Bearer loom-dev-token" \
  -H "Content-Type: application/json" \
  -d '{"confirmed": true}' \
  http://localhost:8000/api/skills/deadlines/<id>
```

### Manual sync

The "Sync now" button on the overview reaches the extension's service worker through the content script, using `window.postMessage` on the dashboard origin. This avoids `chrome.runtime.sendMessage(extensionId, ...)`, which would need the extension's ID configured — and that ID changes between unpacked installs.

The protocol lives in `shared/bridge/dashboard-protocol.ts` and relays only `bridge:ping`, `sync:get-status`, and `sync:now`, so a page cannot use the bridge to drive arbitrary extension messages. Allowed origins default to `localhost:3000` and `127.0.0.1:3000`; a deployed dashboard is authorised by adding its origin to `loom:bridge-origins` in `chrome.storage.sync`.

If the extension is not installed, nothing answers the ping and the panel says so instead of hanging.

### Keeping types in sync

`dashboard/src/lib/types.ts` is hand-written rather than generated, so the dashboard builds without a codegen step. `backend/tests/test_dashboard_types_parity.py` compares those interfaces against the backend's OpenAPI schema field by field, so renaming a field on one side and not the other fails the backend suite.

## PDF Layer

Chrome's built-in PDF viewer is sandboxed, so content scripts cannot read PDF text. LOOM intercepts PDF navigations and renders them with its own pdf.js viewer instead, which makes the text (and any interactive form fields) available to the rest of the extension.

```
extension/src/pdf/
├── types.ts           # Shared types, PDF URL detection, viewer URL helpers
├── interceptor.ts     # Redirects PDF navigations to the LOOM viewer
├── pdf-loader.ts      # pdf.js document loading + per-page text extraction
├── pdf-form.ts        # pdf-lib AcroForm read/write/download
├── pdf-api.ts         # In-memory registry of loaded documents
├── messages.ts        # Message-bus access from content scripts / popup
├── viewer-render.ts   # Canvas + selectable text layer rendering
├── viewer.html/.css/.ts  # The viewer page itself
└── index.ts           # Internal API for the viewer context
```

### Reading PDF content

From the viewer context, import the API directly:

```ts
import { loomPdf } from "@/pdf";

loomPdf.getAllText(url);            // full document text
loomPdf.getPageText(url, 3);        // text of page 3
loomPdf.getSnapshot(url);           // { numPages, pages[], usingFallback, ... }
```

From a content script or the popup, route through the background message bus. Import from `pdf/messages` so pdf.js and pdf-lib stay out of those bundles:

```ts
import { requestPdfSnapshot, requestPdfForm } from "@/pdf/messages";

const snapshot = await requestPdfSnapshot({ tabId });
const form = await requestPdfForm({ url: snapshot.url });
```

Raw PDF bytes are deliberately never sent over the message bus — they stay in the viewer page, which is where filling and downloading happen.

### Reading and writing form fields

```ts
const form = loomPdf.getFormFields(url);
// form.hasFormFields === false  → not a fillable PDF (skip or flag it)
// form.fields → [{ name, type, value, options? }]

await loomPdf.saveFilledPdf(url, { full_name: "Ada Lovelace", agree: true });
```

### Fallback behavior

If pdf.js cannot render a file, the viewer shows a muted warning banner explaining that content capture is unavailable for that document and offers a link to open it in Chrome's default viewer. The snapshot is still recorded with `usingFallback: true` so downstream skills can skip it.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for backend, Postgres, Redis, dashboard)
- [Node.js](https://nodejs.org/) 20.9+ for the extension, and for the dashboard, since Next.js 16 requires it
- [Python](https://www.python.org/) 3.12+ (for running the backend or its tests outside Docker)
- [Google Chrome](https://www.google.com/chrome/) (for loading the extension)

## Quick Start (Docker)

1. Clone the repository and enter the project directory:

   ```bash
   cd loom
   ```

2. Start all services:

   ```bash
   docker compose up --build
   ```

3. Open the dashboard at [http://localhost:3000](http://localhost:3000).

4. The API is available at [http://localhost:8000](http://localhost:8000). Health check: [http://localhost:8000/health](http://localhost:8000/health).

## Extension Development

The extension is built separately and loaded into Chrome as an unpacked extension.

1. Install dependencies and build:

   ```bash
   cd extension
   npm install
   npm run dev
   ```

   `npm run dev` starts Vite in watch mode and outputs to `extension/dist/`.

2. Load the extension in Chrome:

   - Open `chrome://extensions`
   - Enable **Developer mode** (top-right toggle)
   - Click **Load unpacked**
   - Select the `extension/dist` folder

3. After code changes, Vite rebuilds automatically. Click the refresh icon on the extension card in `chrome://extensions` to reload.

4. To open local PDFs with LOOM's viewer, enable **Allow access to file URLs** on the extension's details page in `chrome://extensions`.

### Production build

```bash
cd extension
npm run build
```

The production bundle is in `extension/dist/`.

## Backend Development (without Docker)

1. Create a virtual environment and install dependencies:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements-dev.txt   # or requirements.txt without test tooling
   ```

2. Start Postgres and Redis (via Docker or locally), then set environment variables:

   ```bash
   export DATABASE_URL=postgresql+asyncpg://loom:loom@localhost:5432/loom
   export REDIS_URL=redis://localhost:6379/0
   export CORS_ORIGINS=http://localhost:3000
   ```

3. Run migrations and start the server:

   ```bash
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```

### Tests

```bash
cd backend
pytest          # no Postgres or Redis required
ruff check app tests
```

The suite covers schema contracts, prompt rendering, the classification retry loop, dedup identity, the router's generated SQL, and the API wiring. Redis and the model provider are replaced with in-memory fakes, so anything requiring a live database is left to the `curl` checks above.

Two of these tests exist because the failure they catch is otherwise silent:

- `test_classification_schema.py` asserts the generated JSON schema stays acceptable to provider strict mode, which Pydantic breaks the moment a field gains a default or a `Field(ge=...)` constraint.
- `test_migration_parity.py` compares the mapped models against the migration's column declarations, standing in for the Alembic autogenerate diff that would need a live database.

## Dashboard Development (without Docker)

```bash
cd dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Point it at a backend with `LOOM_API_URL` and `LOOM_API_TOKEN` if the defaults (`http://localhost:8000`, `loom-dev-token`) are wrong.

```bash
npm run lint        # eslint directly; Next 16 removed `next lint`
npm run typecheck
npm run build
```

Two Next 16 details worth knowing before editing config:

- Turbopack is the default bundler and refuses to resolve paths that escape its root, which breaks the `../shared` imports. `next.config.mjs` sets `turbopack.root` to the monorepo root to allow them.
- `next build` no longer runs ESLint at all, so `npm run lint` has to be invoked separately in CI. Rules live in `eslint.config.mjs` (flat config).

The dashboard image is built from the monorepo root rather than `dashboard/`, for the same reason: a `./dashboard` build context would leave `shared/` out of the image.

## Database Migrations

Run from the `backend/` directory:

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

Inside Docker:

```bash
docker compose exec backend alembic upgrade head
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://loom:loom@localhost:5432/loom` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `STUB_AUTH_TOKEN` | Shared bearer when `AUTH_MODE=stub` (local only) | `loom-dev-token` |
| `STUB_USER_ID` | User all stub requests map to | `dev-user` |
| `AUTH_MODE` | `stub` (dev) or `jwt` (per-user / Clerk JWKS) | `stub` |
| `ENVIRONMENT` | `production` refuses stub auth **and** stub AI/embeddings at startup | `development` |
| `JWT_SECRET` / `JWT_JWKS_URL` | HS256 secret and/or Clerk JWKS for JWT mode | see `.env.example` |
| `SENTRY_DSN` | Optional API (and dashboard) error reporting | — |
| `AI_PROVIDER` | `claude`, `openai`, or `stub` (offline heuristics) | `stub` |
| `AI_API_KEY` | Provider key; empty falls back to `stub` | — |
| `AI_BASE_URL` | OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `AI_MODEL` | Model used for classification | `gpt-4o-mini` |
| `LOOM_API_URL` | Backend URL the dashboard fetches from (server-side) | `http://localhost:8000` |
| `LOOM_API_TOKEN` | Bearer token the dashboard sends (server-side) | `loom-dev-token` |

See `backend/.env.example` for the full list, including ingest limits and worker tuning.

## Background Worker

The API only queues work; a separate worker process performs it.

```bash
cd backend
python -m app.worker
```

This runs two consumers concurrently in one process — capture persistence and classification — on separate streams with separate consumer groups, so they can be split into separate deployments without code changes. Both share the claim/read/backoff loop in `app/worker/loop.py`.

Under Docker this runs as the `worker` service. Later phases (contradiction watching, listing re-checks, document diffs) add their own consumers alongside these.

## License

Private — all rights reserved.
