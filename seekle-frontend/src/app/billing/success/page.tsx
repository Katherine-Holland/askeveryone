// src/app/billing/success/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

export default function BillingSuccessPage() {
  const sp = useSearchParams();
  const [checkoutSessionId, setCheckoutSessionId] = useState<string | null>(null);

  useEffect(() => {
    const sid = sp.get("session_id"); // this is Stripe checkout session id (per backend success_url)
    setCheckoutSessionId(sid);
  }, [sp]);

  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-zinc-50 text-zinc-900">
      <div className="w-full max-w-lg rounded-2xl border bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Payment successful 🎉</h1>
        <p className="mt-2 text-sm text-zinc-600">
          Your subscription is being activated. If it doesn’t reflect immediately, refresh in a moment.
        </p>

        {checkoutSessionId ? (
          <div className="mt-4 text-xs text-zinc-500 break-all">
            Checkout session: {checkoutSessionId}
          </div>
        ) : null}

        <a
          href="/"
          className="mt-6 inline-flex items-center justify-center rounded-xl bg-black px-4 py-3 text-sm font-medium text-white"
        >
          Back to Seekle
        </a>
      </div>
    </main>
  );
}
