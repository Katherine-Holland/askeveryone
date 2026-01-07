"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { verifyMagicToken } from "@/lib/api";

export default function VerifyPage() {
  const router = useRouter();
  const sp = useSearchParams();
  const token = sp.get("token");

  const [status, setStatus] = useState<"verifying" | "ok" | "error">("verifying");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function run() {
      if (!token) {
        setStatus("error");
        setError("Missing token.");
        return;
      }
      try {
        await verifyMagicToken({ token });
        setStatus("ok");
        // redirect home (session is now attached server-side)
        setTimeout(() => router.replace("/"), 400);
      } catch (e: any) {
        setStatus("error");
        setError(e?.message || "Verification failed.");
      }
    }
    run();
  }, [token, router]);

  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-zinc-50 text-zinc-900">
      <div className="w-full max-w-md rounded-2xl border bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Signing you in…</h1>

        {status === "verifying" ? (
          <p className="mt-2 text-sm text-zinc-600">Verifying your link.</p>
        ) : null}

        {status === "ok" ? (
          <p className="mt-2 text-sm text-emerald-700">Verified. Redirecting…</p>
        ) : null}

        {status === "error" ? (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 whitespace-pre-wrap">
            {error}
          </div>
        ) : null}
      </div>
    </main>
  );
}
