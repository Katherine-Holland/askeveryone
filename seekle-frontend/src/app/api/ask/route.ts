// src/app/api/ask/route.ts
import { NextResponse } from "next/server";

const RAW_BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "https://askeveryone.onrender.com";

type AskPayload = {
  query: string;
  session_id: string;
  compare?: boolean;
};

function safeBackendUrl(raw: string): string {
  // Render internal URLs often look like: http://askeveryone:10000
  // Public URLs should be https://...
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
    /^[a-z0-9-]+$/.test(url.hostname); // allow simple Render service name like "askeveryone"

  if (isLocalishHost) {
    if (url.protocol !== "http:") {
      throw new Error(`Internal backend must use http:// (got ${url.protocol})`);
    }
  } else {
    if (url.protocol !== "https:") {
      throw new Error(`Public backend must use https:// (got ${url.protocol})`);
    }
  }

  return url.toString().replace(/\/+$/, "");
}

const BACKEND_URL = safeBackendUrl(RAW_BACKEND_URL);

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as AskPayload | null;

  if (!body?.query || !body?.session_id) {
    return NextResponse.json(
      { detail: "query and session_id are required" },
      { status: 400 }
    );
  }

  // Forward useful client headers (helps anon gating)
  // IMPORTANT: append x-forwarded-for rather than overwriting it
  const headers: Record<string, string> = { "Content-Type": "application/json" };

  const incomingXff = req.headers.get("x-forwarded-for");
  const clientIp =
    req.headers.get("true-client-ip") ||
    req.headers.get("x-real-ip") ||
    req.headers.get("cf-connecting-ip") ||
    "";

  if (incomingXff && clientIp) headers["x-forwarded-for"] = `${incomingXff}, ${clientIp}`;
  else if (incomingXff) headers["x-forwarded-for"] = incomingXff;
  else if (clientIp) headers["x-forwarded-for"] = clientIp;

  const xReal = req.headers.get("x-real-ip");
  if (xReal) headers["x-real-ip"] = xReal;

  const trueClient = req.headers.get("true-client-ip");
  if (trueClient) headers["true-client-ip"] = trueClient;

  const cfIp = req.headers.get("cf-connecting-ip");
  if (cfIp) headers["cf-connecting-ip"] = cfIp;

  const ua = req.headers.get("user-agent");
  if (ua) headers["user-agent"] = ua;

  // Prevent infinite hangs
  const controller = new AbortController();
  const timeoutMs = 10_000;
  const t = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const upstream = await fetch(`${BACKEND_URL}/ask`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
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

      return NextResponse.json(
        { detail, backend_status: upstream.status },
        { status: upstream.status }
      );
    }

    return NextResponse.json(payload ?? {}, { status: 200 });
  } catch (e: any) {
    const msg =
      e?.name === "AbortError"
        ? `Upstream timeout (${timeoutMs}ms)`
        : e?.message || "unknown";

    return NextResponse.json(
      { detail: `Upstream fetch failed: ${msg}`, backend_url: BACKEND_URL },
      { status: 502 }
    );
  } finally {
    clearTimeout(t);
  }
}
