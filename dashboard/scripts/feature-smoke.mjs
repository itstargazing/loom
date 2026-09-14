/**
 * End-to-end feature smoke as a temporary Clerk user.
 *
 * Creates a throwaway Clerk user + session JWT, exercises API surfaces the
 * dashboard depends on, probes unauthenticated dashboard route reachability,
 * then deletes the user.
 *
 * Usage (from dashboard/):
 *   node --env-file=.env.local scripts/feature-smoke.mjs
 */

import { createClerkClient } from "@clerk/backend";

const API = process.env.LOOM_API_URL ?? "http://127.0.0.1:8000";
const DASH = process.env.LOOM_DASH_URL ?? "http://127.0.0.1:3000";
const secret = process.env.CLERK_SECRET_KEY;

if (!secret) {
  console.error("CLERK_SECRET_KEY missing (.env.local)");
  process.exit(1);
}

const clerk = createClerkClient({ secretKey: secret });

const results = [];

function record(area, name, ok, detail = "") {
  results.push({ area, name, ok, detail: String(detail).slice(0, 240) });
  const mark = ok ? "PASS" : "FAIL";
  console.log(`[${mark}] ${area} :: ${name}${detail ? ` — ${detail}` : ""}`);
}

async function api(token, method, path, { body, expect } = {}) {
  const response = await fetch(`${API}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }
  const expected = expect ?? [200];
  const ok = expected.includes(response.status);
  return { ok, status: response.status, json, text, expected };
}

async function main() {
  const email = `loom-smoke-${Date.now()}@example.com`;
  const password = `Loom-smoke-${Date.now()}!aA1`;
  let user;
  let session;

  try {
    user = await clerk.users.createUser({
      emailAddress: [email],
      password,
      skipPasswordChecks: true,
      skipPasswordRequirement: true,
    });
    session = await clerk.sessions.createSession({ userId: user.id });

    let tokenPayload = await clerk.sessions.getToken(session.id);
    let token = tokenPayload.jwt;

    // Prefer the loom JWT template when the instance has one configured.
    try {
      const loom = await clerk.sessions.getToken(session.id, "loom");
      if (loom?.jwt) token = loom.jwt;
    } catch {
      // Template may be missing on accountless instances; default session JWT is fine.
    }

    record("auth", "create temporary Clerk user", true, user.id);

    {
      const me = await api(token, "GET", "/api/auth/me");
      record(
        "auth",
        "GET /api/auth/me",
        me.ok && me.json?.userId === user.id,
        me.ok ? `userId=${me.json?.userId}` : `${me.status} ${me.text}`,
      );
    }

    {
      const status = await api(token, "GET", "/api/auth/status", { expect: [200] });
      // status may be public — still try with token
      record("auth", "GET /api/auth/status", status.ok, `${status.status}`);
    }

    const getChecks = [
      ["/api/overview", [200]],
      ["/api/digest", [200]],
      ["/api/trail", [200]],
      ["/api/notifications", [200]],
      ["/api/briefs", [200]],
      ["/api/privacy/settings", [200]],
      ["/api/privacy/local-mode?url=https://example.local/path", [200]],
      ["/api/classifications?limit=5", [200]],
      ["/api/classifications/stats", [200]],
      ["/api/collections", [200]],
      ["/api/capture/events?limit=5", [200]],
      ["/api/skills/glossary?limit=5", [200]],
      ["/api/skills/citations?limit=5", [200]],
      ["/api/skills/citations/export", [200]],
      ["/api/skills/deadlines?limit=5", [200]],
      ["/api/skills/contradictions?limit=5", [200]],
      ["/api/skills/contradiction-claims?limit=5", [200]],
      ["/api/skills/reading?limit=5", [200]],
      ["/api/skills/reading/compile", [200]],
      ["/api/skills/reading/export?format=md", [200, 204]],
      ["/api/skills/products?limit=5", [200]],
      ["/api/skills/products/compare", [200]],
      ["/api/skills/products/export", [200, 204]],
      ["/api/skills/jobs?limit=5", [200]],
      ["/api/skills/contract-flags?limit=5", [200]],
      ["/api/skills/form-filler/profiles", [200]],
      ["/api/skills/form-filler/documents", [200]],
      ["/api/skills/live-doc-diff/sets", [200]],
      ["/api/skills/live-doc-diff/unread", [200]],
      ["/api/skills/auto-attach/documents", [200]],
    ];

    for (const [path, expect] of getChecks) {
      const res = await api(token, "GET", path, { expect });
      record("api-get", `GET ${path}`, res.ok, res.ok ? "" : `${res.status} ${res.text}`);
    }

    {
      const ask = await api(token, "POST", "/api/ask", {
        body: { question: "What did I capture recently?" },
        expect: [200],
      });
      record("api-write", "POST /api/ask", ask.ok, ask.ok ? "" : `${ask.status} ${ask.text}`);
    }

    {
      const brief = await api(token, "POST", "/api/briefs", {
        body: { topic: "smoke test brief" },
        expect: [200, 201],
      });
      record(
        "api-write",
        "POST /api/briefs",
        brief.ok,
        brief.ok ? "" : `${brief.status} ${brief.text}`,
      );
    }

    {
      const collection = await api(token, "POST", "/api/collections", {
        body: { name: "Smoke collection", kind: "citation" },
        expect: [200, 201],
      });
      record(
        "api-write",
        "POST /api/collections",
        collection.ok,
        collection.ok
          ? `id=${collection.json?.id ?? "?"}`
          : `${collection.status} ${collection.text}`,
      );

      if (collection.ok && collection.json?.id) {
        const del = await api(token, "DELETE", `/api/collections/${collection.json.id}`, {
          expect: [200, 204],
        });
        record(
          "api-write",
          "DELETE /api/collections/{id}",
          del.ok,
          del.ok ? "" : `${del.status} ${del.text}`,
        );
      }
    }

    {
      const profile = await api(token, "POST", "/api/skills/form-filler/profiles", {
        body: {
          name: "Smoke profile",
          fields: { full_name: "Smoke Tester", email: email },
        },
        expect: [200, 201],
      });
      record(
        "api-write",
        "POST /api/skills/form-filler/profiles",
        profile.ok,
        profile.ok
          ? `id=${profile.json?.id ?? "?"}`
          : `${profile.status} ${profile.text}`,
      );

      if (profile.ok && profile.json?.id) {
        const del = await api(
          token,
          "DELETE",
          `/api/skills/form-filler/profiles/${profile.json.id}`,
          { expect: [200, 204] },
        );
        record(
          "api-write",
          "DELETE form-filler profile",
          del.ok,
          del.ok ? "" : `${del.status} ${del.text}`,
        );
      }
    }

    {
      const set = await api(token, "POST", "/api/skills/live-doc-diff/sets", {
        body: { name: "Smoke set" },
        expect: [200, 201],
      });
      record(
        "api-write",
        "POST /api/skills/live-doc-diff/sets",
        set.ok,
        set.ok ? `id=${set.json?.id ?? "?"}` : `${set.status} ${set.text}`,
      );

      if (set.ok && set.json?.id) {
        const del = await api(token, "DELETE", `/api/skills/live-doc-diff/sets/${set.json.id}`, {
          expect: [200, 204],
        });
        record(
          "api-write",
          "DELETE live-doc-diff set",
          del.ok,
          del.ok ? "" : `${del.status} ${del.text}`,
        );
      }
    }

    {
      const privacy = await api(token, "PUT", "/api/privacy/settings", {
        body: {
          localOnlyDomains: ["example.local"],
        },
        expect: [200],
      });
      record(
        "api-write",
        "PUT /api/privacy/settings",
        privacy.ok,
        privacy.ok ? "" : `${privacy.status} ${privacy.text}`,
      );
    }

    {
      const capture = await api(token, "POST", "/api/capture/events", {
        body: {
          events: [
            {
              id: crypto.randomUUID(),
              type: "highlight_selected",
              sourceUrl: "https://example.com/smoke",
              pageTitle: "Smoke page",
              timestamp: new Date().toISOString(),
              payload: {
                selectedText:
                  "Photosynthesis converts light into chemical energy. Final paper due December 12, 2026.",
              },
            },
          ],
        },
        expect: [200, 201, 202],
      });
      record(
        "api-write",
        "POST /api/capture/events",
        capture.ok,
        capture.ok ? JSON.stringify(capture.json).slice(0, 120) : `${capture.status} ${capture.text}`,
      );
    }

    {
      const account = await api(token, "PATCH", "/api/auth/me", {
        body: { displayName: "Smoke Tester" },
        expect: [200],
      });
      record(
        "api-write",
        "PATCH /api/auth/me",
        account.ok,
        account.ok ? "" : `${account.status} ${account.text}`,
      );
    }

    // Dashboard route reachability (Clerk gate → expect redirect or 200).
    const pages = [
      "/",
      "/sign-in",
      "/digest",
      "/ask",
      "/trail",
      "/account",
      "/privacy",
      "/style-guide",
      "/skills/glossary",
      "/skills/citations",
      "/skills/deadlines",
      "/skills/contradictions",
      "/skills/reading",
      "/skills/products",
      "/skills/jobs",
      "/skills/contract-flags",
      "/skills/form-filler",
      "/skills/live-doc-diff",
      "/skills/auto-attach",
    ];

    for (const path of pages) {
      try {
        const response = await fetch(`${DASH}${path}`, {
          redirect: "manual",
          signal: AbortSignal.timeout(20_000),
        });
        // Unauthenticated app routes should redirect to sign-in; public auth pages 200.
        const publicPage = path.startsWith("/sign-");
        const ok = publicPage
          ? response.status === 200
          : response.status === 200 ||
            response.status === 307 ||
            response.status === 302 ||
            response.status === 303;
        record(
          "dashboard",
          path,
          ok,
          `status=${response.status} loc=${response.headers.get("location") ?? ""}`,
        );
      } catch (error) {
        record("dashboard", path, false, error instanceof Error ? error.message : String(error));
      }
    }

    {
      const health = await fetch(`${API}/health`);
      record("infra", "GET /health", health.ok, `status=${health.status}`);
    }
  } finally {
    await Promise.allSettled([
      session ? clerk.sessions.revokeSession(session.id) : Promise.resolve(),
      user ? clerk.users.deleteUser(user.id) : Promise.resolve(),
    ]);
    if (user) record("auth", "cleanup temp Clerk user", true, user.id);
  }

  const failed = results.filter((r) => !r.ok);
  const passed = results.filter((r) => r.ok);
  console.log("\n==== SUMMARY ====");
  console.log(`passed=${passed.length} failed=${failed.length} total=${results.length}`);
  if (failed.length) {
    console.log("\nFailures:");
    for (const f of failed) {
      console.log(`- [${f.area}] ${f.name}: ${f.detail}`);
    }
  }
  console.log(
    "\nNote: dashboard checks are unauthenticated HTTP only (no browser session). Interactive UI, Sync now, and extension capture were not click-tested.",
  );
  process.exitCode = failed.length ? 1 : 0;
}

await main();
