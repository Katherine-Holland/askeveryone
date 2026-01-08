// src/app/auth/verify/verify-client.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { verifyMagicLink } from "@/lib/api";

export default function VerifyClient() {
  const router = useRouter();
  const sp = useSearchParams();

  const [status, setStatus] = useState<"verifying" | "ok" | "error">("verifying");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = sp.get("token");
    if (!token) {
      setStatus("error");
      setError("Missing token. Please open the full link from your email.");
      return;
    }

    (async () => {
      try {
        await verifyMagicLink({ token });
        setStatus("ok");
        // send them back home after verify
        router.replace("/");
      } catch (e: any) {
        setStatus("error");
        setError(e?.message || "Could not verify link.");
      }
    })();
  }, [sp, router]);

  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-zinc-50 text-zinc-900">
      <div className="w-full max-w-md rounded-2xl border bg-white p-5 shadow">
        {status === "verifying" ? (
          <div className="text-sm text-zinc-600">Verifying your link…</div>
        ) : null}

        {status === "ok" ? (
          <div className="text-sm text-emerald-700">Verified. Redirecting…</div>
        ) : null}

        {status === "error" ? (
          <div className="text-sm text-red-700 whitespace-pre-wrap">
            {error || "Verification failed."}
          </div>
        ) : null}
      </div>
    </main>
  );
}
