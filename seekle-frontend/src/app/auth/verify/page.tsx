// src/app/auth/verify/page.tsx
import { Suspense } from "react";
import VerifyClient from "./verify-client";

export default function VerifyPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen flex items-center justify-center p-6">
          <div className="w-full max-w-md rounded-2xl border bg-white p-5 shadow">
            <div className="text-sm text-zinc-600">Verifying your link…</div>
          </div>
        </main>
      }
    >
      <VerifyClient />
    </Suspense>
  );
}
