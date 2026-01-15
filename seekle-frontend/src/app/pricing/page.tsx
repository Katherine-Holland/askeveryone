// src/app/pricing/page.tsx
"use client";

import { useEffect, useState } from "react";
import UpgradeEmailModal from "@/components/UpgradeEmailModal";

type Plan = "starter" | "plus" | "power";

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
    `/api/billing/checkout?session_id=${encodeURIComponent(session_id)}&plan=${encodeURIComponent(plan)}`,
    { method: "POST", cache: "no-store" }
  );

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || "Checkout failed");

  if (data?.url) {
    window.location.href = data.url;
    return;
  }
  throw new Error("Checkout not configured yet (missing url).");
}

export default function PricingPage() {
  const [loadingPlan, setLoadingPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [needEmail, setNeedEmail] = useState(false);
  const [pendingPlan, setPendingPlan] = useState<Plan | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => setSessionId(getSessionId()), []);

  async function onChoose(plan: Plan) {
    setError(null);

    const sid = sessionId || getSessionId();
    if (!sid) {
      setError("Session not ready. Refresh and try again.");
      return;
    }

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
      await ensureLoggedForBilling(sid, email);
      await startCheckout(pendingPlan, sid);
    } catch (e: any) {
      setError(e?.message || "Something went wrong");
    } finally {
      setLoadingPlan(null);
      setPendingPlan(null);
    }
  }

  return (
    <main className="min-h-screen bg-seekle-cream text-seekle-text p-6">
      <div className="mx-auto w-full max-w-5xl">
        <div className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Upgrade</h1>
            <p className="mt-2 text-sm text-seekle-subtext">
              Seekle Pro and Seekle Power are coming soon.
            </p>
          </div>

          <a
            href="/"
            className="rounded-full border border-seekle-border bg-white px-4 py-2 text-sm text-seekle-subtext hover:bg-seekle-muted"
          >
            Back
          </a>
        </div>

        {error ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-white p-4 text-sm text-red-700 whitespace-pre-wrap shadow-soft">
            {error}
          </div>
        ) : null}

        {/* Launch offer header */}
        <div className="mb-6 rounded-2xl border border-seekle-border bg-white p-5 shadow-soft">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="text-sm text-seekle-subtext">Launch offer</div>
              <div className="mt-1 text-base">
                Starter is discounted for early users.
                <span className="ml-2 inline-flex items-center rounded-full bg-seekle-muted px-3 py-1 text-xs text-seekle-subtext">
                  Limited time
                </span>
              </div>
            </div>
            <div className="text-sm text-seekle-subtext">
              Previous price: <span className="line-through">£16/mo</span> &nbsp;→&nbsp;{" "}
              <span className="font-semibold text-seekle-text">£6/mo</span>
            </div>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {/* Starter (LIVE) */}
          <div className="rounded-3xl border border-seekle-border bg-white p-7 shadow-soft">
            <div className="flex items-center justify-between">
              <div className="text-sm text-seekle-subtext">Starter</div>
              <span className="rounded-full bg-seekle-muted px-3 py-1 text-xs text-seekle-subtext">
                Live
              </span>
            </div>

            <div className="mt-3 flex items-end gap-2">
              <div className="text-4xl font-semibold tracking-tight">£6</div>
              <div className="pb-1 text-sm text-seekle-subtext">/ month</div>
            </div>

            <div className="mt-3 text-sm text-seekle-subtext">
              Start seeking with our starter pack! Starter: 200 credits/month (1 credit = 1 search).
            </div>

            <ul className="mt-6 space-y-2 text-sm text-seekle-text">
              <li>• Switches between models for seamless chat</li>
              <li>• 200 searches a month</li>
              <li>• Saved conversations</li>
              <li>• Models included: ChatGPT, Perplexity, Gemini, Claude & Grok</li>
            </ul>

            <button
              type="button"
              onClick={() => void onChoose("starter")}
              disabled={!!loadingPlan}
              className="mt-7 w-full rounded-full px-5 py-3 border border-transparent bg-seekle-brown text-white hover:bg-seekle-brownHover disabled:opacity-50"
            >
              {loadingPlan === "starter" ? "Loading…" : "Choose Starter"}
            </button>

            <div className="mt-3 text-xs text-seekle-subtext">
              Secure payment via Stripe.
            </div>
          </div>

          {/* Plus (COMING SOON) */}
          <div className="rounded-3xl border border-seekle-border bg-white/70 p-7 opacity-70">
            <div className="flex items-center justify-between">
              <div className="text-sm text-seekle-subtext">Pro</div>
              <span className="rounded-full bg-seekle-muted px-3 py-1 text-xs text-seekle-subtext">
                Coming soon. Seek knowledge with more tokens, become a Pro Seekler!
              </span>
            </div>

            <div className="mt-3 text-3xl font-semibold tracking-tight">—</div>
            <div className="mt-3 text-sm text-seekle-subtext">
              More features coming soon.
            </div>

            <ul className="mt-6 space-y-2 text-sm text-seekle-text">
              <li>• Ad Free</li>
              <li>• Export/import tools</li>
              <li>• Integrations</li>
            </ul>

            <div className="mt-7 w-full rounded-full px-5 py-3 border border-seekle-border bg-white text-seekle-subtext text-center cursor-not-allowed">
              Not available yet
            </div>
          </div>

          {/* Power (COMING SOON) */}
          <div className="rounded-3xl border border-seekle-border bg-white/70 p-7 opacity-70">
            <div className="flex items-center justify-between">
              <div className="text-sm text-seekle-subtext">Power</div>
              <span className="rounded-full bg-seekle-muted px-3 py-1 text-xs text-seekle-subtext">
                Coming soon. Choose Power Mode to seek like a Boss!
              </span>
            </div>

            <div className="mt-3 text-3xl font-semibold tracking-tight">—</div>
            <div className="mt-3 text-sm text-seekle-subtext">
              Plus, advanced workflows for developers.
            </div>

            <ul className="mt-6 space-y-2 text-sm text-seekle-text">
              <li>• Intent Logging</li>
              <li>• Build mode</li>
              <li>• Secret Stuff</li>
            </ul>

            <div className="mt-7 w-full rounded-full px-5 py-3 border border-seekle-border bg-white text-seekle-subtext text-center cursor-not-allowed">
              Not available yet
            </div>
          </div>
        </div>

        <div className="mt-10 text-xs text-seekle-subtext">
          Starter is the only paid plan right now. Plus/Power will launch once the ecosystem features are live.
        </div>
      </div>

      <UpgradeEmailModal
        open={needEmail}
        onClose={() => {
          setNeedEmail(false);
          setPendingPlan(null);
        }}
        onSuccess={(email: string) => void onEmailContinue(email)}
      />
    </main>
  );
}
