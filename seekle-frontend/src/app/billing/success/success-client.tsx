// src/app/billing/success/success-client.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

type BillingStatus = {
  ok: boolean;
  user_id: string;
  plan: string;
  credits_balance: number;
};

async function fetchBillingStatus(sessionId: string): Promise<BillingStatus> {
  const r = await fetch(`/api/billing/status?session_id=${encodeURIComponent(sessionId)}`, {
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
  const [plan, setPlan] = useState<string | null>(null);

  useEffect(() => {
    const sessionId = sp.get("session_id"); // Stripe Checkout Session id in your success_url
    if (!sessionId) {
      setStatus("error");
      setError("Missing session_id.");
      return;
    }

    let cancelled = false;

    // Stripe webhook can be slightly delayed, so poll briefly
    (async () => {
      try {
        for (let i = 0; i < 8; i++) {
          const st = await fetchBillingStatus(sessionId);
          if (cancelled) return;

          // We expect paid after webhook processes
          if ((st.plan || "").toLowerCase() === "paid") {
            setPlan(st.plan);
            setStatus("ok");

            // go home after a beat (or to /account later)
            setTimeout(() => router.replace("/"), 900);
            return;
          }

          // wait 700ms then retry
          await new Promise((res) => setTimeout(res, 700));
        }

        // if still not paid after retries, don't fail hard — just send home
        setPlan("pending");
        setStatus("ok");
        setTimeout(() => router.replace("/"), 1200);
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
          <p className="mt-2 text-sm text-zinc-600">
            Confirming your subscription…
          </p>
        ) : null}

        {status === "ok" ? (
          <p className="mt-2 text-sm text-emerald-700">
            {plan === "paid"
              ? "You’re subscribed. Redirecting…"
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
