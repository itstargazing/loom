import { NextRequest, NextResponse } from "next/server";

/**
 * Server-side proxy so the browser can mutate skill stores without holding the
 * backend token. The dashboard already fetches on the server with LOOM_API_TOKEN;
 * this is the equivalent for PATCH/DELETE/POST from client components.
 *
 * Request and response bodies are forwarded as bytes so PDF uploads and zip
 * downloads are not corrupted by UTF-8 text decoding.
 */

const API_BASE_URL = process.env.LOOM_API_URL ?? "http://localhost:8000";
const AUTH_TOKEN = process.env.LOOM_API_TOKEN ?? "loom-dev-token";

async function proxy(
  request: NextRequest,
  path: string[],
): Promise<NextResponse> {
  const upstream = new URL(`/api/${path.join("/")}`, API_BASE_URL);
  upstream.search = request.nextUrl.search;

  const headers: Record<string, string> = {
    Authorization: `Bearer ${AUTH_TOKEN}`,
  };
  const contentType = request.headers.get("content-type") ?? "";
  const method = request.method;
  const isMultipart = contentType.includes("multipart/form-data");

  let body: BodyInit | undefined;
  if (method !== "GET" && method !== "HEAD") {
    if (isMultipart) {
      const inbound = await request.formData();
      const outbound = new FormData();
      for (const [key, value] of inbound.entries()) {
        if (typeof value === "string") {
          outbound.append(key, value);
        } else {
          const bytes = await value.arrayBuffer();
          outbound.append(
            key,
            new Blob([bytes], { type: value.type || "application/octet-stream" }),
            value.name,
          );
        }
      }
      body = outbound;
    } else {
      const inbound = await request.arrayBuffer();
      body = inbound.byteLength > 0 ? inbound : undefined;
      if (contentType) headers["Content-Type"] = contentType;
    }
  }

  let response: Response;
  try {
    response = await fetch(upstream, {
      method,
      headers,
      body,
      cache: "no-store",
    });
  } catch {
    const onVercel =
      process.env.VERCEL === "1" &&
      (API_BASE_URL.includes("localhost") || API_BASE_URL.includes("127.0.0.1"));
    return NextResponse.json(
      {
        detail: onVercel
          ? "This Vercel deploy has no public API. Set LOOM_API_URL to a hosted FastAPI URL (not localhost) and redeploy."
          : `Cannot reach the backend at ${API_BASE_URL}.`,
      },
      { status: 502 },
    );
  }

  const outboundBody = await response.arrayBuffer();
  const outbound: Record<string, string> = {
    "Content-Type": response.headers.get("content-type") ?? "application/json",
  };
  const disposition = response.headers.get("content-disposition");
  if (disposition) outbound["Content-Disposition"] = disposition;
  return new NextResponse(outboundBody, {
    status: response.status,
    headers: outbound,
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, (await context.params).path);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, (await context.params).path);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxy(request, (await context.params).path);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxy(request, (await context.params).path);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxy(request, (await context.params).path);
}
