// src/app/api/billing/checkout/route.ts
import { NextResponse } from "next/server";

const RAW_BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "https://askeveryone.onrender.com";

type Plan = "starter" | "plus" | "power";

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
  const { searchParams } = new URL(req.url);
  const session_id = searchParams.get("session_id");
  const plan = (searchParams.get("plan") || "").toLowerCase().trim() as Plan;

  if (!session_id) {
    return NextResponse.json({ detail: "session_id is required" }, { status: 400 });
  }
  if (!plan || !["starter", "plus", "power"].includes(plan)) {
    return NextResponse.json(
      { detail: "plan must be starter|plus|power" },
      { status: 400 }
    );
  }

  const controller = new AbortController();
  const timeoutMs = 15_000;
  const t = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const upstream = await fetch(
      `${BACKEND_URL}/billing/checkout?session_id=${encodeURIComponent(
        session_id
      )}&plan=${encodeURIComponent(plan)}`,
      {
        method: "POST",
        cache: "no-store",
        signal: controller.signal,
        headers: {
          ...(req.headers.get("user-agent")
            ? { "user-agent": req.headers.get("user-agent") as string }
            : {}),
        },
      }
    );

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
