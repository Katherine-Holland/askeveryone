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
};

export type BillingStatusResponse = {
  ok: boolean;
  user_id: string;
  plan: string; // "free" | "paid" (today)
  credits_balance: number;
};

export type Plan = "starter" | "plus" | "power";

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

      // FastAPI validation errors: { detail: [{loc, msg, type}, ...] }
      if (Array.isArray(data?.detail)) {
        return data.detail
          .map((e: any) => e?.msg || JSON.stringify(e))
          .join(", ");
      }

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
    }),
  });

  if (!r.ok) {
    const msg = await parseBackendError(r);
    throw new Error(`Backend ${r.status}: ${msg}`);
  }

  return (await r.json()) as AskResponse;
}

// --------------------
// Auth (Magic Link) — proxied
// --------------------

export async function requestMagicLink(args: { email: string; session_id: string }) {
  const r = await fetch(`/api/auth/request-link`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
    cache: "no-store",
  });

  if (!r.ok) {
    const msg = await parseBackendError(r);
    throw new Error(`Backend ${r.status}: ${msg}`);
  }

  return (await r.json()) as { ok: boolean };
}


export async function verifyMagicLink(args: { token: string }) {
  const r = await fetch(`/api/auth/verify?token=${encodeURIComponent(args.token)}`, {
    method: "GET",
    cache: "no-store",
  });

  if (!r.ok) {
    const msg = await parseBackendError(r);
    throw new Error(`Backend ${r.status}: ${msg}`);
  }

  return (await r.json()) as { ok: boolean; user_id: string; session_id: string };
}

// --------------------
// Billing — proxied
// --------------------

export async function getBillingStatus(session_id: string): Promise<BillingStatusResponse> {
  const r = await fetch(`/api/billing/status?session_id=${encodeURIComponent(session_id)}`, {
    method: "GET",
    cache: "no-store",
  });

  if (!r.ok) {
    const msg = await parseBackendError(r);
    throw new Error(`Backend ${r.status}: ${msg}`);
  }

  return (await r.json()) as BillingStatusResponse;
}

/**
 * Starts Stripe Checkout and returns the URL.
 * UI should redirect browser to url.
 */
export async function createCheckout(session_id: string, plan: Plan): Promise<{ ok: boolean; url: string }> {
  const r = await fetch(
    `/api/billing/checkout?session_id=${encodeURIComponent(session_id)}&plan=${encodeURIComponent(plan)}`,
    { method: "POST", cache: "no-store" }
  );

  if (!r.ok) {
    const msg = await parseBackendError(r);
    throw new Error(`Backend ${r.status}: ${msg}`);
  }

  return (await r.json()) as { ok: boolean; url: string };
}
