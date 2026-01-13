"use client";

import { useEffect, useState } from "react";
import UpgradeEmailModal from "@/components/UpgradeEmailModal";

type Plan = "starter";

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
  const res = await fetch(
    `/api/billing/checkout?session_id=${encodeURIComponent(
      session_id
    )}&plan=${encodeURIComponent(plan)}`,
    { method: "POST", cache: "no-store" }
  );

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || "Checkout failed");

  if (data?.url) {
    window.location.href = data.url;
    return;
  }

  throw new Error("Checkout not configured yet");
}

export default function PricingPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [needEmail, setNeedEmail] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    setSessionId(getSessionId());
  }, []);

  async function onChooseStarter() {
    setError(null);
    if (!sessionId) {
      setError("Session not ready. Please refresh.");
      return;
    }
    setNeedEmail(true);
  }

  async function onEmailContinue(email: string) {
    if (!sessionId) return;

    setNeedEmail(false);
    setLoading(true);
    setError(null);

    try {
      await ensureLoggedForBilling(sessionId, email);
      await startCheckout("starter", sessionId);
    } catch (e: any) {
      setError(e?.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-zinc-50 text-zinc-900 p-6">
      <div className="mx-auto w-full max-w-4xl">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Upgrade</h1>
            <p className="mt-2 text-sm text-zinc-600">
              Simple pricing. More features coming soon.
            </p>
          </div>

          <a
            href="/"
            className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm text-zinc-700 hover:bg-zinc-100"
          >
            Back
          </a>
        </div>

        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-white p-4 text-sm text-red-600">
            {error}
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-3">
          {/* Starter */}
          <div className="rounded-2xl border border-zinc-200 bg-white p-6">
            <div className="text-sm text-zinc-500">Starter</div>
            <div className="mt-2 text-3xl font-semibold">£6 / month</div>
            <div className="mt-2 text-sm text-zinc-600">
              Ad-free Seekle with higher daily usage.
            </div>

            <ul className="mt-5 space-y-2 text-sm text-zinc-700">
              <li>• No ads</li>
              <li>• Higher daily query limits</li>
              <li>• Saved conversations</li>
              <li>• Full access to all current tools</li>
            </ul>

            <button
              type="button"
              onClick={onChooseStarter}
              disabled={loading}
              className="mt-6 w-full rounded-full px-5 py-3 border bg-black text-white disabled:opacity-50"
            >
              {loading ? "Loading…" : "Upgrade to Starter"}
            </button>
          </div>

          {/* Plus – Coming Soon */}
          <div className="rounded-2xl border border-zinc-200 bg-zinc-100 p-6 opacity-60">
            <div className="text-sm text-zinc-500">Plus</div>
            <div className="mt-2 text-2xl font-semibold">Coming soon</div>
            <div className="mt-2 text-sm text-zinc-600">
              Ecosystem features and deeper integrations.
            </div>

            <ul className="mt-5 space-y-2 text-sm text-zinc-700">
              <li>• Tool comparisons</li>
              <li>• Extended context</li>
              <li>• Integrations (Slack, HubSpot)</li>
            </ul>

            <div className="mt-6 w-full rounded-full px-5 py-3 border text-center text-sm text-zinc-500 bg-zinc-200">
              Coming soon
            </div>
          </div>

          {/* Power – Coming Soon */}
          <div className="rounded-2xl border border-zinc-200 bg-zinc-100 p-6 opacity-60">
            <div className="text-sm text-zinc-500">Power</div>
            <div className="mt-2 text-2xl font-semibold">Coming soon</div>
            <div className="mt-2 text-sm text-zinc-600">
              Advanced workflows and team features.
            </div>

            <ul className="mt-5 space-y-2 text-sm text-zinc-700">
              <li>• .chat & ChatterScript exports</li>
              <li>• Snapshots & audit logs</li>
              <li>• Team collaboration</li>
            </ul>

            <div className="mt-6 w-full rounded-full px-5 py-3 border text-center text-sm text-zinc-500 bg-zinc-200">
              Coming soon
            </div>
          </div>
        </div>

        <div className="mt-8 text-xs text-zinc-500">
          Payments are processed securely by Stripe.
        </div>
      </div>

      <UpgradeEmailModal
        open={needEmail}
        onClose={() => setNeedEmail(false)}
        onSuccess={onEmailContinue}
      />
    </main>
  );
}
