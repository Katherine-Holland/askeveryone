// src/app/billing/cancel/page.tsx
"use client";

export default function BillingCancelPage() {
  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-zinc-50 text-zinc-900">
      <div className="w-full max-w-lg rounded-2xl border bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Checkout cancelled</h1>
        <p className="mt-2 text-sm text-zinc-600">
          No worries — you can upgrade any time.
        </p>

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
