import { Suspense } from "react";
import VerifyClient from "./verify-client";

export default function VerifyPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen flex items-center justify-center p-6 bg-zinc-50 text-zinc-900">
          <div className="w-full max-w-md rounded-2xl border bg-white p-6 shadow-sm">
            <h1 className="text-xl font-semibold">Signing you in…</h1>
            <p className="mt-2 text-sm text-zinc-600">Loading…</p>
          </div>
        </main>
      }
    >
      <VerifyClient />
    </Suspense>
  );
}
