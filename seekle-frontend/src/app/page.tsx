"use client";

import { useEffect, useState } from "react";
import { askBackend, isPaywallError, type AskResponse } from "@/lib/api";
import LoginModal from "@/components/LoginModal";
import AccountMenu from "@/components/AccountMenu";

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

function resetSessionId(): string {
  const key = "seekle_session_id";
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

  // Optional: dev-only debug visibility (off by default)
  const [debug, setDebug] = useState(false);

  useEffect(() => {
    setMounted(true);
    setSessionId(getOrCreateSessionId());
    if (process.env.NODE_ENV === "development") setDebug(false);
  }, []);

  async function runAsk() {
    const q = query.trim();
    if (!q || !sessionId || loading) return;

    setLoading(true);
    setError(null);

    try {
      const out = await askBackend({ query: q, session_id: sessionId });
      setResp(out);
      setQuery(""); // ✅ clears input after asking
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

  const canShowDebug = process.env.NODE_ENV === "development";

  function onLogout() {
    // Clear UI + create a fresh anonymous session id
    setResp(null);
    setError(null);
    setQuery("");

    const newId = resetSessionId();
    setSessionId(newId);
  }

  function onUpgrade() {
    // Task: we'll build /pricing next, but for now route there.
    window.location.href = "/pricing";
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-zinc-50 text-zinc-900">
      <div className="w-full max-w-2xl">
        {/* Top row: brand left, account right */}
        <div className="flex items-center justify-between mb-8">
          <div className="text-left">
            <h1 className="text-4xl font-semibold tracking-tight">Seekle</h1>
            <p className="mt-2 text-sm text-zinc-600">Ask Everyone.</p>
          </div>

          {mounted ? (
            <AccountMenu
              sessionId={sessionId}
              onLogout={onLogout}
              onUpgrade={onUpgrade}
              usageLabel={undefined} // placeholder for now
            />
          ) : null}
        </div>

        {/* No <form> — avoids refresh */}
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

        {/* Dev-only debug toggle */}
        {mounted && canShowDebug ? (
          <div className="mt-8 flex items-center justify-center gap-3 text-xs text-zinc-400">
            <button
              type="button"
              onClick={() => setDebug((v) => !v)}
              className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-zinc-500 hover:text-zinc-700"
            >
              {debug ? "Hide debug" : "Show debug"}
            </button>

            {debug ? <span className="select-all">Session: {sessionId}</span> : null}
          </div>
        ) : null}

        <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} sessionId={sessionId} />
      </div>
    </main>
  );
}
