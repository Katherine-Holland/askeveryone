"use client";

import { useEffect, useState } from "react";
import UpgradeEmailModal from "@/components/UpgradeEmailModal";

type Plan = "starter" | "pro" | "business";

function getSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("seekle_session_id");
}

async function ensureLoggedForBilling(session_id: string, email: string) {
  const res = await fetch("/api/billing/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify({ session_id, email }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || "Could not start billing");
  return data;
}

async function startCheckout(plan: Plan, session_id: string) {
  const res = await fetch(`/api/billing/checkout?session_id=${encodeURIComponent(session_id)}&plan=${encodeURIComponent(plan)}`, {
    method: "POST",
    cache: "no-store",
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || "Checkout failed");

  if (data?.url) window.location.href = data.url;
  throw new Error("Checkout not configured yet (missing url).");
}

export default function PricingPage() {
  const [loadingPlan, setLoadingPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [needEmail, setNeedEmail] = useState(false);
  const [pendingPlan, setPendingPlan] = useState<Plan | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    setSessionId(getSessionId());
  }, []);

  async function onChoose(plan: Plan) {
    setError(null);
    const sid = sessionId || getSessionId();
    if (!sid) {
      setError("Session not ready. Refresh and try again.");
      return;
    }

    // We *don’t* force login first anymore.
    // We’ll prompt email and attach session -> user server-side.
    setPendingPlan(plan);
    setNeedEmail(true);
  }

  async function onEmailContinue(email: string) {
    const sid = sessionId || getSessionId();
    if (!sid || !pendingPlan) return;

    setNeedEmail(false);
    setLoadingPlan(pendingPlan);
    setError(null);

    try {
      // Attach user to this session_id (upgrade-first)
      await ensureLoggedForBilling(sid, email);

      // Now run checkout
      await startCheckout(pendingPlan, sid);
    } catch (e: any) {
      setError(e?.message || "Something went wrong");
    } finally {
      setLoadingPlan(null);
      setPendingPlan(null);
    }
  }

  return (
    <main className="min-h-screen bg-zinc-50 text-zinc-900 p-6">
      <div className="mx-auto w-full max-w-4xl">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Upgrade</h1>
            <p className="mt-2 text-sm text-zinc-600">
              Pick a plan. You can change or cancel later.
            </p>
          </div>

          <a
            href="/"
            className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm text-zinc-700 hover:bg-zinc-100"
          >
            Back
          </a>
        </div>

        {error ? (
          <div className="mb-6 rounded-xl border border-red-200 bg-white p-4 text-sm text-red-600 whitespace-pre-wrap">
            {error}
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-3">
          {/* Starter */}
          <div className="rounded-2xl border border-zinc-200 bg-white p-6">
            <div className="text-sm text-zinc-500">Starter</div>
            <div className="mt-2 text-3xl font-semibold">Free</div>
            <div className="mt-2 text-sm text-zinc-600">
              Basic access for trying Seekle.
            </div>

            <ul className="mt-5 space-y-2 text-sm text-zinc-700">
              <li>• Limited daily searches</li>
              <li>• Saved conversation (basic)</li>
              <li>• Standard speed</li>
            </ul>

            <button
              type="button"
              disabled
              className="mt-6 w-full rounded-full px-5 py-3 border bg-zinc-100 text-zinc-400 cursor-not-allowed"
            >
              Current plan
            </button>
          </div>

          {/* Pro */}
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="text-sm text-zinc-500">Pro</div>
            <div className="mt-2 text-3xl font-semibold">£19/mo</div>
            <div className="mt-2 text-sm text-zinc-600">
              For regular use and power searching.
            </div>

            <ul className="mt-5 space-y-2 text-sm text-zinc-700">
              <li>• Higher daily limits</li>
              <li>• Conversation history</li>
              <li>• Faster providers</li>
              <li>• Priority routing</li>
            </ul>

            <button
              type="button"
              onClick={() => void onChoose("pro")}
              disabled={!!loadingPlan}
              className="mt-6 w-full rounded-full px-5 py-3 border bg-black text-white disabled:opacity-50"
            >
              {loadingPlan === "pro" ? "Loading…" : "Choose Pro"}
            </button>
          </div>

          {/* Business */}
          <div className="rounded-2xl border border-zinc-200 bg-white p-6">
            <div className="text-sm text-zinc-500">Business</div>
            <div className="mt-2 text-3xl font-semibold">£49/mo</div>
            <div className="mt-2 text-sm text-zinc-600">
              Team usage + higher limits.
            </div>

            <ul className="mt-5 space-y-2 text-sm text-zinc-700">
              <li>• Highest daily limits</li>
              <li>• Team-ready usage</li>
              <li>• Priority support</li>
              <li>• Best routing + fallbacks</li>
            </ul>

            <button
              type="button"
              onClick={() => void onChoose("business")}
              disabled={!!loadingPlan}
              className="mt-6 w-full rounded-full px-5 py-3 border bg-black text-white disabled:opacity-50"
            >
              {loadingPlan === "business" ? "Loading…" : "Choose Business"}
            </button>
          </div>
        </div>

        <div className="mt-8 text-xs text-zinc-500">
          Payments are processed securely by Stripe.
        </div>
      </div>

      <UpgradeEmailModal
        open={needEmail}
        onClose={() => {
          setNeedEmail(false);
          setPendingPlan(null);
        }}
        onSuccess={(email) => void onEmailContinue(email)}
      />
    </main>
  );
}
