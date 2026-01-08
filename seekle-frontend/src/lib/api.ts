// src/lib/api.ts
export type AskResponse = {
  query_id: string;
  answer: string;
  intent: string;
  provider_used: string;
  providers_called: string[];
  confidence: number;
  multi_call: boolean;
  meta?: any;
};

export type AskRequest = {
  query: string;
  session_id: string;
  compare?: boolean;
  turnstile_token?: string;
};

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "https://askeveryone.onrender.com";

/**
 * Helpful for UI logic:
 * - if error contains "Backend 402:" you can open LoginModal / show paywall CTA
 */
export function isPaywallError(err: unknown): boolean {
  const msg = err instanceof Error ? err.message : String(err);
  return msg.includes("Backend 402:");
}

async function parseBackendError(r: Response): Promise<string> {
  const contentType = r.headers.get("content-type") || "";

  try {
    if (contentType.includes("application/json")) {
      const data = await r.json();
      if (data?.detail) return String(data.detail);
      if (data?.message) return String(data.message);
      return JSON.stringify(data);
    }
  } catch {
    // ignore
  }

  try {
    const text = await r.text();
    return text || "Unknown error";
  } catch {
    return "Unknown error";
  }
}

/**
 * Ask route
 * ✅ Uses Next.js API route (/api/ask) to avoid CORS + "failed to fetch"
 */
export async function askBackend(args: AskRequest): Promise<AskResponse> {
  const r = await fetch(`/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: args.query,
      session_id: args.session_id,
      ...(args.compare ? { compare: true } : {}),
      ...(args.turnstile_token ? { turnstile_token: args.turnstile_token } : {}),
    }),
  });

  if (!r.ok) {
    const msg = await parseBackendError(r);
    throw new Error(`Backend ${r.status}: ${msg}`);
  }

  return (await r.json()) as AskResponse;
}

// --------------------
// Auth (Magic Link)
// --------------------
// You can keep these direct to BACKEND_URL for now.
// Later we can proxy them too (same pattern) if you want everything under /api/*.

export async function requestMagicLink(args: { email: string; session_id: string }) {
  const params = new URLSearchParams({
    email: args.email,
    session_id: args.session_id,
  });

  const r = await fetch(`${BACKEND_URL}/auth/request-link?${params.toString()}`, {
    method: "POST",
  });

  if (!r.ok) {
    const msg = await parseBackendError(r);
    throw new Error(`Backend ${r.status}: ${msg}`);
  }

  return (await r.json()) as { ok: boolean };
}

export async function verifyMagicLink(args: { token: string }) {
  const params = new URLSearchParams({ token: args.token });

  const r = await fetch(`${BACKEND_URL}/auth/verify?${params.toString()}`, {
    method: "GET",
  });

  if (!r.ok) {
    const msg = await parseBackendError(r);
    throw new Error(`Backend ${r.status}: ${msg}`);
  }

  return (await r.json()) as { ok: boolean; user_id: string; session_id: string };
}
