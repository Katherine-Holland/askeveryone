import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "https://askeveryone.onrender.com";

type AskPayload = {
  query: string;
  session_id: string;
  compare?: boolean;
  turnstile_token?: string;
};

export async function POST(req: Request) {
  let body: AskPayload;

  try {
    body = (await req.json()) as AskPayload;
  } catch {
    return NextResponse.json(
      { detail: "Invalid JSON body" },
      { status: 400 }
    );
  }

  if (!body?.query || !body?.session_id) {
    return NextResponse.json(
      { detail: "query and session_id are required" },
      { status: 400 }
    );
  }

  // Forward client IP headers (helps your anon gating + logging)
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const fwd = req.headers.get("x-forwarded-for");
  if (fwd) headers["x-forwarded-for"] = fwd;

  const realIp = req.headers.get("x-real-ip");
  if (realIp) headers["x-real-ip"] = realIp;

  const cfIp = req.headers.get("cf-connecting-ip");
  if (cfIp) headers["cf-connecting-ip"] = cfIp;

  const ua = req.headers.get("user-agent");
  if (ua) headers["user-agent"] = ua;

  try {
    const upstream = await fetch(`${BACKEND_URL}/ask`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      // avoid caching in Next for dynamic requests
      cache: "no-store",
    });

    const contentType = upstream.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");

    // Try to parse upstream response
    const payload = isJson ? await upstream.json().catch(() => null) : null;
    const text = !isJson ? await upstream.text().catch(() => "") : "";

    if (!upstream.ok) {
      // Preserve backend status (e.g. 402) and detail message
      const detail =
        (payload && (payload.detail || payload.message)) ||
        text ||
        `Backend error (${upstream.status})`;

      return NextResponse.json(
        { detail },
        { status: upstream.status }
      );
    }

    return NextResponse.json(payload ?? {}, { status: 200 });
  } catch (e: any) {
    return NextResponse.json(
      { detail: `Upstream fetch failed: ${e?.message || "unknown"}` },
      { status: 502 }
    );
  }
}
