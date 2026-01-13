// app/pricing/page.tsx
"use client";

import { useState } from "react";

type Plan = "starter" | "pro" | "power";

async function startCheckout(plan: Plan) {
  const session_id =
    typeof window !== "undefined"
      ? localStorage.getItem("seekle_session_id")
      : null;

  const res = await fetch("/api/billing/checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // Backend can accept either JSON body OR query params depending on your proxy.
    // We keep body-based here (matches your current page).
    body: JSON.stringify({ plan, session_id }),
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data?.detail || "Checkout failed");
  }

  if (data?.url) {
    window.location.href = data.url;
    return;
  }

  throw new Error("Checkout not configured yet (missing url).");
}

function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "promo" | "soon";
}) {
  const cls =
    tone === "promo"
      ? "border-amber-200 bg-amber-50 text-amber-800"
      : tone === "soon"
      ? "border-sky-200 bg-sky-50 text-sky-800"
      : "border-zinc-200 bg-white text-zinc-600";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${cls}`}
    >
      {children}
    </span>
  );
}

export default function PricingPage() {
  const [loadingPlan, setLoadingPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onChoose(plan: Plan) {
    setError(null);
    setLoadingPlan(plan);
    try {
      await startCheckout(plan);
    } catch (e: any) {
      setError(e?.message || "Something went wrong");
    } finally {
      setLoadingPlan(null);
    }
  }

  return (
    <main className="min-h-screen bg-zinc-50 text-zinc-900 p-6">
      <div className="mx-auto w-full max-w-5xl">
        {/* Header */}
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between mb-10">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl md:text-4xl font-semibold tracking-tight">
                Pricing
              </h1>
              <Badge tone="promo">Launch offer</Badge>
            </div>

            <p className="mt-3 text-sm text-zinc-600 max-w-2xl">
              Everyone gets access to the same Seekle intelligence and providers.
              Plans only change <span className="font-medium">Seekle features</span>{" "}
              (history, exports, integrations) — not answer quality.
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <Badge tone="promo">Limited-time pricing</Badge>
              <Badge tone="neutral">Ads on Free + Starter</Badge>
              <Badge tone="soon">Pro / Power: coming soon</Badge>
            </div>
          </div>

          <a
            href="/"
            className="inline-flex items-center justify-center rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm text-zinc-700 hover:bg-zinc-100"
          >
            Back to Seekle
          </a>
        </div>

        {error ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-white p-4 text-sm text-red-600 whitespace-pre-wrap">
            {error}
          </div>
        ) : null}

        {/* Cards */}
        <div className="grid gap-4 md:grid-cols-3">
          {/* Free */}
          <div className="rounded-3xl border border-zinc-200 bg-white p-6">
            <div className="flex items-center justify-between">
              <div className="text-sm text-zinc-500">Free</div>
              <Badge>Starter access</Badge>
            </div>

            <div className="mt-3 text-4xl font-semibold tracking-tight">£0</div>
            <div className="mt-2 text-sm text-zinc-600">
              Try Seekle. Lightweight usage with ads.
            </div>

            <ul className="mt-6 space-y-2 text-sm text-zinc-700">
              <li>• Limited daily searches</li>
              <li>• Ads enabled</li>
              <li>• Basic conversation (session-based)</li>
              <li>• Same providers + routing as paid</li>
            </ul>

            <button
              type="button"
              disabled
              className="mt-7 w-full rounded-full px-5 py-3 border bg-zinc-100 text-zinc-400 cursor-not-allowed"
            >
              Current plan
            </button>

            <p className="mt-3 text-xs text-zinc-500">
              You’re not penalised on quality — just usage and features.
            </p>
          </div>

          {/* Starter (LIVE) */}
          <div className="rounded-3xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="text-sm text-zinc-500">Starter</div>
              <Badge tone="promo">Best for launch</Badge>
            </div>

            <div className="mt-3 flex items-end gap-2">
              <div className="text-4xl font-semibold tracking-tight">£6</div>
              <div className="pb-1 text-sm text-zinc-500">
                /mo{" "}
                <span className="ml-2 line-through text-zinc-400">£10</span>
              </div>
            </div>

            <div className="mt-2 text-sm text-zinc-600">
              More usage + saved history. <span className="font-medium">Ads stay on</span>.
            </div>

            <ul className="mt-6 space-y-2 text-sm text-zinc-700">
              <li>• Higher daily limits</li>
              <li>• Saved conversation history</li>
              <li>• Export: copy / markdown</li>
              <li>• Ads enabled (launch)</li>
              <li>• Same providers + routing as everyone</li>
            </ul>

            <button
              type="button"
              onClick={() => void onChoose("starter")}
              disabled={!!loadingPlan}
              className="mt-7 w-full rounded-full px-5 py-3 border bg-black text-white disabled:opacity-50"
            >
              {loadingPlan === "starter" ? "Loading…" : "Upgrade to Starter"}
            </button>

            <p className="mt-3 text-xs text-zinc-500">
              Launch pricing is limited-time. You can cancel anytime.
            </p>
          </div>

          {/* Pro / Power (COMING SOON) */}
          <div className="rounded-3xl border border-zinc-200 bg-white p-6">
            <div className="flex items-center justify-between">
              <div className="text-sm text-zinc-500">Pro + Power</div>
              <Badge tone="soon">Coming soon</Badge>
            </div>

            <div className="mt-3 text-4xl font-semibold tracking-tight">Soon</div>
            <div className="mt-2 text-sm text-zinc-600">
              Ecosystem features — not “better answers”.
            </div>

            <ul className="mt-6 space-y-2 text-sm text-zinc-700">
              <li>• Integrations (Slack / HubSpot)</li>
              <li>• Compare mode (multi-model debugging)</li>
              <li>• Projects + snapshots</li>
              <li>• .chat exports + Chatterscript ecosystem</li>
              <li>• Voice add-on (planned)</li>
            </ul>

            <button
              type="button"
              disabled
              className="mt-7 w-full rounded-full px-5 py-3 border bg-zinc-100 text-zinc-400 cursor-not-allowed"
            >
              Notify me (soon)
            </button>

            <p className="mt-3 text-xs text-zinc-500">
              We’ll ship these after Starter is stable and loved.
            </p>
          </div>
        </div>

        {/* Footer note */}
        <div className="mt-10 rounded-3xl border border-zinc-200 bg-white p-6">
          <div className="text-sm font-medium">What doesn’t change by plan</div>
          <p className="mt-2 text-sm text-zinc-600">
            Seekle’s routing + providers stay the same for everyone. Plans change
            access, history, exports, and ecosystem features — not intelligence.
          </p>

          <div className="mt-4 text-xs text-zinc-500">
            Payments are processed securely by Stripe. (We’ll wire this next.)
          </div>
        </div>
      </div>
    </main>
  );
}
