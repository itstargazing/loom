/**
 * Isolation check: two Clerk users → two different LOOM /api/auth/me userIds.
 *
 * Usage (from dashboard/): node --env-file=.env.local scripts/verify-clerk-isolation.mjs
 * Requires backend AUTH_MODE=jwt with Clerk JWKS, and LOOM_API_URL reachable.
 */

import { createClerkClient } from "@clerk/backend";

const API = process.env.LOOM_API_URL ?? "http://127.0.0.1:8000";
const secret = process.env.CLERK_SECRET_KEY;
if (!secret) {
  console.error("CLERK_SECRET_KEY missing");
  process.exit(1);
}

const clerk = createClerkClient({ secretKey: secret });

async function makeUser(label) {
  const email = `loom-${label}-${Date.now()}@example.com`;
  const user = await clerk.users.createUser({
    emailAddress: [email],
    password: `Loom-test-${label}-${Date.now()}!aA1`,
    skipPasswordChecks: true,
    skipPasswordRequirement: true,
  });
  const session = await clerk.sessions.createSession({ userId: user.id });
  const token = await clerk.sessions.getToken(session.id);
  return { label, userId: user.id, email, token: token.jwt, sessionId: session.id };
}

async function loomMe(token) {
  const response = await fetch(`${API}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await response.json().catch(() => ({}));
  return { status: response.status, body, detail: body.detail ?? null };
}

const a = await makeUser("a");
const b = await makeUser("b");

try {
  const meA = await loomMe(a.token);
  const meB = await loomMe(b.token);

  console.log(
    JSON.stringify(
      {
        api: API,
        a: {
          clerkUserId: a.userId,
          loomStatus: meA.status,
          loomUserId: meA.body.userId,
          detail: meA.detail,
        },
        b: {
          clerkUserId: b.userId,
          loomStatus: meB.status,
          loomUserId: meB.body.userId,
          detail: meB.detail,
        },
        isolated:
          meA.status === 200 &&
          meB.status === 200 &&
          meA.body.userId === a.userId &&
          meB.body.userId === b.userId &&
          meA.body.userId !== meB.body.userId,
      },
      null,
      2,
    ),
  );

  if (
    !(
      meA.status === 200 &&
      meB.status === 200 &&
      meA.body.userId !== meB.body.userId
    )
  ) {
    process.exitCode = 1;
  }
} finally {
  await Promise.allSettled([
    clerk.sessions.revokeSession(a.sessionId),
    clerk.sessions.revokeSession(b.sessionId),
    clerk.users.deleteUser(a.userId),
    clerk.users.deleteUser(b.userId),
  ]);
}
