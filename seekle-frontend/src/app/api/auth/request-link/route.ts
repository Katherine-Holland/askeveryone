// src/app/api/auth/request-link/route.ts
import { NextResponse } from "next/server";

const RAW_BACKEND_URL =
  (process.env.NODE_ENV !== "production" ? process.env.BACKEND_URL_DEV : undefined) ||
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "https://askeveryone.onrender.com";

type Payload = { email: string; session_id: string };

function safeBackendUrl(raw: string): string {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    throw new Error(`Invalid BACKEND_URL: ${raw}`);
  }

  const isLocalishHost =
    url.hostname === "localhost" ||
    url.hostname === "127.0.0.1" ||
    url.hostname.endsWith(".internal") ||
    /^[a-z0-9-]+$/.test(url.hostname);

  if (isLocalishHost) {
    if (url.protocol !== "http:") throw new Error(`Internal backend must use http:// (got ${url.protocol})`);
  } else {
    if (url.protocol !== "https:") throw new Error(`Public backend must use https:// (got ${url.protocol})`);
  }

  return url.toString().replace(/\/+$/, "");
}

const BACKEND_URL = safeBackendUrl(RAW_BACKEND_URL);

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as Payload | null;

  if (!body?.email || !body?.session_id) {
    return NextResponse.json({ detail: "email and session_id are required" }, { status: 400 });
  }

  const params = new URLSearchParams({
    email: body.email,
    session_id: body.session_id,
  });

  const headers: Record<string, string> = {};
  const ua = req.headers.get("user-agent");
  if (ua) headers["user-agent"] = ua;

  const controller = new AbortController();
  const timeoutMs = 10_000;
  const t = setTimeout(() => controller.abort(), timeoutMs);

  try {
    // ✅ backend expects query params, not JSON body
    const upstream = await fetch(`${BACKEND_URL}/auth/request-link?${params.toString()}`, {
      method: "POST",
      headers,
      cache: "no-store",
      signal: controller.signal,
    });

    const contentType = upstream.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");

    const payload = isJson ? await upstream.json().catch(() => null) : null;
    const text = !isJson ? await upstream.text().catch(() => "") : "";

    if (!upstream.ok) {
      const detail =
        (payload && (payload.detail || payload.message)) ||
        text ||
        `Backend error (${upstream.status})`;

      return NextResponse.json({ detail, backend_status: upstream.status }, { status: upstream.status });
    }

    return NextResponse.json(payload ?? { ok: true }, { status: 200 });
  } catch (e: any) {
    const msg = e?.name === "AbortError" ? `Upstream timeout (${timeoutMs}ms)` : e?.message || "unknown";
    return NextResponse.json({ detail: `Upstream fetch failed: ${msg}`, backend_url: BACKEND_URL }, { status: 502 });
  } finally {
    clearTimeout(t);
  }
}
