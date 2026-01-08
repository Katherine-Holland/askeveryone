"use client";

import { useEffect, useState } from "react";
import { askBackend, isPaywallError, type AskResponse } from "@/lib/api";
import LoginModal from "@/components/LoginModal";

function getOrCreateSessionId(): string {
  const key = "seekle_session_id";
  const existing = localStorage.getItem(key);
  if (existing) return existing;

  const id =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random()}`;

  localStorage.setItem(key, id);
  return id;
}

export default function Home() {
  const [mounted, setMounted] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  const [resp, setResp] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [loginOpen, setLoginOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
    setSessionId(getOrCreateSessionId());
  }, []);

  async function runAsk() {
    const q = query.trim();
    if (!q || !sessionId || loading) return;

    setLoading(true);
    setError(null);

    try {
      const out = await askBackend({ query: q, session_id: sessionId });
      setResp(out);
    } catch (err: any) {
      if (isPaywallError(err)) {
        setLoginOpen(true);
        setError(null);
      } else {
        setError(err?.message || "Something went wrong");
      }
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
        </div>

        {/* No <form> — avoids any chance of navigation refresh */}
        <div className="flex gap-2 items-center">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask or type..."
            className="flex-1 rounded-full border border-zinc-200 bg-white px-5 py-3 text-base outline-none focus:ring-2 focus:ring-black/10"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void runAsk();
              }
            }}
          />

          <button
            type="button"
            onClick={() => void runAsk()}
            disabled={loading || !query.trim() || !sessionId}
            className="rounded-full px-5 py-3 border bg-black text-white disabled:opacity-50"
          >
            {loading ? "Asking…" : "Search"}
          </button>
        </div>

        <div className="mt-8 space-y-3">
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

        {mounted ? (
          <div className="mt-8 text-center text-xs text-zinc-400">
            Session: {sessionId}
          </div>
        ) : (
          <div className="mt-8 text-center text-xs text-zinc-400">Session: …</div>
        )}

        <LoginModal
          open={loginOpen}
          onClose={() => setLoginOpen(false)}
          sessionId={sessionId}
        />
      </div>
    </main>
  );
}
