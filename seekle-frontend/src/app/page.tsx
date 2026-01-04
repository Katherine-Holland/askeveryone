"use client";

import { useEffect, useMemo, useState } from "react";
import { askBackend, type AskResponse } from "@/lib/api";
import Turnstile from "@/components/Turnstile";

function getOrCreateSessionId(): string {
  // Simple client-side session id for now (uuid via crypto)
  const key = "seekle_session_id";
  const existing = typeof window !== "undefined" ? localStorage.getItem(key) : null;
  if (existing) return existing;

  const id =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random()}`;

  localStorage.setItem(key, id);
  return id;
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [resp, setResp] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Turnstile token for anonymous 1 free query
  const [turnstileToken, setTurnstileToken] = useState("");

  const sessionId = useMemo(() => {
    if (typeof window === "undefined") return "";
    return getOrCreateSessionId();
  }, []);

  useEffect(() => {
    // Optional: warm the backend or display session_id if you want
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;

    setLoading(true);
    setError(null);
    setResp(null);

    try {
      const out = await askBackend({
        query: q,
        session_id: sessionId,
        // ✅ pass Turnstile token (backend requires it for anonymous)
        turnstile_token: turnstileToken || undefined,
      });
      setResp(out);
    } catch (err: any) {
      setError(err?.message || "Something went wrong");

      // If Turnstile fails/expired, force the user to complete again
      setTurnstileToken("");
    } finally {
      setLoading(false);
    }
  }

  const canSearch = !!query.trim() && !!turnstileToken && !loading;

  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <h1 className="text-5xl font-semibold tracking-tight">Seekle</h1>
          <p className="mt-3 text-sm text-muted-foreground opacity-80">
            Ask Everyone
          </p>
        </div>

        <form onSubmit={onSubmit} className="flex flex-col gap-3 items-center">
          <div className="w-full flex gap-2 items-center">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask or type..."
              className="flex-1 rounded-full border px-5 py-3 text-base outline-none focus:ring-2 focus:ring-black/10"
            />
            <button
              type="submit"
              disabled={!canSearch}
              className="rounded-full px-5 py-3 border bg-black text-white disabled:opacity-50"
            >
              {loading ? "Asking…" : "Ask"}
            </button>
          </div>

          {/* ✅ Turnstile widget */}
          <Turnstile onToken={setTurnstileToken} />

          {!turnstileToken ? (
            <div className="text-xs text-black/50">
              Complete verification to run your free anonymous query.
            </div>
          ) : (
            <div className="text-xs text-black/50">
              Verified ✓ You can run 1 free anonymous query.
            </div>
          )}
        </form>

        {/* Results */}
        <div className="mt-8">
          {error ? (
            <div className="rounded-xl border p-4 text-sm text-red-600 whitespace-pre-wrap">
              {error}
              <div className="mt-2 text-xs text-black/60">
                If this says Turnstile failed/expired, just complete the checkbox again.
              </div>
            </div>
          ) : null}

          {resp ? (
            <div className="rounded-xl border p-5">
              <div className="text-xs text-black/60 mb-2">
                Provider: {resp.provider_used} · Intent: {resp.intent}
              </div>
              <div className="whitespace-pre-wrap leading-7">{resp.answer}</div>
            </div>
          ) : null}
        </div>

        <div className="mt-8 text-center text-xs text-black/40">
          Session: {sessionId || "…"}
        </div>
      </div>
    </main>
  );
}
