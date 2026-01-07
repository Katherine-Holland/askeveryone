"use client";

import { useEffect, useState } from "react";
import { askBackend, type AskResponse } from "@/lib/api";
import LoginModal from "@/components/LoginModal";

function getOrCreateSessionId(): string {
  const key = "seekle_session_id";
  const existing = window.localStorage.getItem(key);
  if (existing) return existing;

  const id =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random()}`;

  window.localStorage.setItem(key, id);
  return id;
}

function isPaywallError(msg: string) {
  const m = msg.toLowerCase();
  // Your backend returns 402 with these phrases
  return (
    m.includes("backend 402") ||
    m.includes("create a free account") ||
    m.includes("free access is busy") ||
    m.includes("out of credits") ||
    m.includes("purchase more") ||
    m.includes("upgrade")
  );
}

export default function Home() {
  const [mounted, setMounted] = useState(false);
  const [sessionId, setSessionId] = useState("");

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [resp, setResp] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [loginOpen, setLoginOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
    setSessionId(getOrCreateSessionId());
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q || !sessionId || loading) return;

    setLoading(true);
    setError(null);
    setResp(null);

    try {
      const out = await askBackend({ query: q, session_id: sessionId });
      setResp(out);
    } catch (err: any) {
      const msg = err?.message || "Something went wrong";
      setError(msg);

      // Auto-open login modal if paywalled
      if (isPaywallError(msg)) setLoginOpen(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-zinc-50 text-zinc-900">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <h1 className="text-5xl font-semibold tracking-tight">Seekle</h1>
          <p className="mt-3 text-sm text-zinc-600">Ask Everyone.</p>

          <div className="mt-4 flex items-center justify-center gap-2">
            <button
              onClick={() => setLoginOpen(true)}
              className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-xs text-zinc-900 hover:bg-zinc-100"
              disabled={!mounted || !sessionId}
              title={!mounted ? "Loading…" : ""}
            >
              Save conversation
            </button>
          </div>
        </div>

        <form onSubmit={onSubmit} className="flex gap-2 items-center">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask or type..."
            className="flex-1 rounded-full border border-zinc-200 bg-white px-5 py-3 text-base outline-none focus:ring-2 focus:ring-black/10"
          />
          <button
            type="submit"
            disabled={!mounted || loading || !query.trim() || !sessionId}
            className="rounded-full px-5 py-3 border bg-black text-white disabled:opacity-50"
          >
            {loading ? "Asking…" : "Search"}
          </button>
        </form>

        <div className="mt-8">
          {error ? (
            <div className="rounded-xl border border-red-200 bg-white p-4 text-sm text-red-600 whitespace-pre-wrap">
              {error}
            </div>
          ) : null}

          {resp ? (
            <div className="rounded-xl border border-zinc-200 bg-white p-5">
              <div className="text-xs text-zinc-500 mb-2">
                Provider: {resp.provider_used} · Intent: {resp.intent}
              </div>
              <div className="whitespace-pre-wrap leading-7">{resp.answer}</div>
            </div>
          ) : null}
        </div>

        <div className="mt-8 text-center text-xs text-zinc-400">
          Session: {mounted ? sessionId : "…"}
        </div>
      </div>

      {/* Login modal */}
      <LoginModal
        open={loginOpen}
        onClose={() => setLoginOpen(false)}
        sessionId={sessionId}
      />
    </main>
  );
}
