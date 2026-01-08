// src/app/api/ask/route.ts
import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "https://askeveryone.onrender.com";

type AskPayload = {
  query: string;
  session_id: string;
  compare?: boolean;
};

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as AskPayload | null;

  if (!body?.query || !body?.session_id) {
    return NextResponse.json({ detail: "query and session_id are required" }, { status: 400 });
  }

  // Forward useful client headers (helps anon gating)
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  for (const h of ["x-forwarded-for", "x-real-ip", "cf-connecting-ip", "user-agent"]) {
    const v = req.headers.get(h);
    if (v) headers[h] = v;
  }

  // ✅ Prevent infinite hangs
  const controller = new AbortController();
  const timeoutMs = 8000;
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
    const msg = e?.name === "AbortError" ? `Upstream timeout (${timeoutMs}ms)` : (e?.message || "unknown");
    return NextResponse.json(
      { detail: `Upstream fetch failed: ${msg}`, backend_url: BACKEND_URL },
      { status: 502 }
    );
  } finally {
    clearTimeout(t);
  }
}
