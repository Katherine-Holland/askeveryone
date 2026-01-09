// src/app/billing/success/page.tsx
import { Suspense } from "react";
import SuccessClient from "./success-client";

export default function BillingSuccessPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen flex items-center justify-center p-6 bg-zinc-50 text-zinc-900">
          <div className="w-full max-w-md rounded-2xl border bg-white p-6 shadow-sm">
            <h1 className="text-xl font-semibold">Finalizing your subscription…</h1>
            <p className="mt-2 text-sm text-zinc-600">Just a moment.</p>
          </div>
        </main>
      }
    >
      <SuccessClient />
    </Suspense>
  );
}
