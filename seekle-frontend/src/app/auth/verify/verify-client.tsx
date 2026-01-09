// src/app/auth/verify/verify-client.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function VerifyClient() {
  const router = useRouter();
  const sp = useSearchParams();

  const [status, setStatus] = useState<"verifying" | "ok" | "error">("verifying");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = sp.get("token");
    if (!token) {
      setStatus("error");
      setError("Missing token.");
      return;
    }

    (async () => {
      try {
        const r = await fetch(`/api/auth/verify?token=${encodeURIComponent(token)}`, {
          method: "GET",
          cache: "no-store",
        });

        const contentType = r.headers.get("content-type") || "";
        const isJson = contentType.includes("application/json");
        const payload = isJson ? await r.json().catch(() => null) : null;
        const text = !isJson ? await r.text().catch(() => "") : "";

        if (!r.ok) {
          const msg =
            (payload && (payload.detail || payload.message)) ||
            text ||
            `Verification failed (${r.status})`;
          throw new Error(msg);
        }

        // If backend returns a session_id, attach it to this device
        if (payload?.session_id) {
          localStorage.setItem("seekle_session_id", String(payload.session_id));
        }

        setStatus("ok");
        router.replace("/");
      } catch (e: any) {
        setStatus("error");
        setError(e?.message || "Verification failed.");
      }
    })();
  }, [sp, router]);

  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-zinc-50 text-zinc-900">
      <div className="w-full max-w-md rounded-2xl border bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Signing you in…</h1>

        {status === "verifying" ? (
          <p className="mt-2 text-sm text-zinc-600">Verifying your magic link.</p>
        ) : null}

        {status === "ok" ? (
          <p className="mt-2 text-sm text-emerald-700">Success. Redirecting…</p>
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
