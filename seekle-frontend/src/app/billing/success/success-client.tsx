"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

type BillingStatus = {
  ok: boolean;
  user_id: string;
  plan: "free" | "paid" | string;
  tier?: string | null;
  credits_balance: number;
};

function getSeekleSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("seekle_session_id");
}

async function fetchBillingStatus(seekleSessionId: string): Promise<BillingStatus> {
  const r = await fetch(`/api/billing/status?session_id=${encodeURIComponent(seekleSessionId)}`, {
    method: "GET",
    cache: "no-store",
  });

  const data = await r.json().catch(() => null);

  if (!r.ok) {
    const msg = data?.detail ? String(data.detail) : `Status error (${r.status})`;
    throw new Error(msg);
  }

  return data as BillingStatus;
}

export default function SuccessClient() {
  const router = useRouter();
  const sp = useSearchParams();

  const [status, setStatus] = useState<"checking" | "ok" | "error">("checking");
  const [error, setError] = useState<string | null>(null);
  const [tier, setTier] = useState<string | null>(null);

  useEffect(() => {
    // This is Stripe's Checkout Session id (cs_...), useful for debug only
    const stripeSessionId = sp.get("stripe_session_id");

    // This is what *your* billing/status endpoint needs
    const seekleSessionId = getSeekleSessionId();

    if (!seekleSessionId) {
      setStatus("error");
      setError("Missing Seekle session. Please go back home and try again.");
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        // Stripe webhook can be delayed, poll briefly
        for (let i = 0; i < 10; i++) {
          const st = await fetchBillingStatus(seekleSessionId);
          if (cancelled) return;

          if ((st.plan || "").toLowerCase() === "paid") {
            setTier(st.tier ?? null);
            setStatus("ok");
            setTimeout(() => router.replace("/"), 900);
            return;
          }

          await new Promise((res) => setTimeout(res, 700));
        }

        // Don't hard fail — payment may still be processing
        setTier("processing");
        setStatus("ok");
        setTimeout(() => router.replace("/"), 1200);

        // Optional: you can console.log stripeSessionId for debugging
        void stripeSessionId;
      } catch (e: any) {
        setStatus("error");
        setError(e?.message || "Could not confirm subscription.");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [sp, router]);

  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-zinc-50 text-zinc-900">
      <div className="w-full max-w-md rounded-2xl border bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Payment successful</h1>

        {status === "checking" ? (
          <p className="mt-2 text-sm text-zinc-600">Confirming your subscription…</p>
        ) : null}

        {status === "ok" ? (
          <p className="mt-2 text-sm text-emerald-700">
            {tier && tier !== "processing"
              ? `You’re subscribed (${tier}). Redirecting…`
              : "Subscription is processing. Redirecting…"}
          </p>
        ) : null}

        {status === "error" ? (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 whitespace-pre-wrap">
            {error}
          </div>
        ) : null}

        <button
          className="mt-5 w-full rounded-xl bg-black px-4 py-3 text-sm font-medium text-white"
          onClick={() => router.replace("/")}
        >
          Go back home
        </button>
      </div>
    </main>
  );
}
