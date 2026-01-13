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

  // Dev-only debug visibility (off by default)
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
      setQuery("");
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

  function onLogout() {
    setResp(null);
    setError(null);
    setQuery("");

    const newId = resetSessionId();
    setSessionId(newId);

    window.location.assign("/");
  }

  function onUpgrade() {
    window.location.href = "/pricing";
  }

  const canShowDebug = process.env.NODE_ENV === "development";

  return (
    <main className="min-h-screen bg-seekle-cream text-seekle-text">
      <div className="fixed top-6 right-6 z-50">
        {mounted ? (
          <AccountMenu
            onLogout={onLogout}
            onUpgrade={onUpgrade}
            usageLabel={undefined}
            debugSession={canShowDebug && debug ? sessionId : null}
          />
        ) : null}
      </div>

      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="w-full max-w-2xl">
          <div className="text-center mb-8">
            <h1 className="text-5xl font-semibold tracking-tight">Seekle</h1>
            <p className="mt-3 text-sm text-zinc-600">Ask Everyone.</p>
          </div>

          <div className="flex gap-2 items-center">
            {/* Always-present glow wrapper, pulses harder only while loading */}
            <div
              className={`seekle-input-wrap flex-1 ${loading ? "is-loading" : ""}`}
            >
              <div className="seekle-input-glow" />
              <div className="seekle-input-sheen" />

              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask or type..."
                className="relative z-10 w-full rounded-full border border-seekle-border bg-white px-5 py-3 text-base outline-none focus:ring-2 focus:ring-black/10"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    void runAsk();
                  }
                }}
              />

              {/* Subtle taupe “listening” dot inside the bar (only while loading) */}
              {loading ? <span className="seekle-bar-dot" aria-hidden /> : null}
            </div>

            <button
              type="button"
              onClick={() => void runAsk()}
              disabled={loading || !query.trim() || !sessionId}
              aria-label="Search"
              className="rounded-full px-5 py-3 border border-transparent bg-seekle-brown text-white hover:bg-seekle-brownHover disabled:opacity-50"
            >
              {/* No “Thinking…” text */}
              Search
            </button>
          </div>

          <div className="mt-8 space-y-3">
            {error ? (
              <div className="rounded-xl border border-red-200 bg-white p-4 text-sm text-red-600 whitespace-pre-wrap">
                {error}
              </div>
            ) : null}

            {resp ? (
              <div className="rounded-xl border border-seekle-border bg-white p-5">
                <div className="text-xs text-zinc-500 mb-2">
                  Provider: {resp.provider_used} · Intent: {resp.intent}
                </div>
                <div className="whitespace-pre-wrap leading-7">{resp.answer}</div>
              </div>
            ) : null}
          </div>

          {mounted && canShowDebug ? (
            <div className="mt-8 flex items-center justify-center gap-3 text-xs text-zinc-400">
              <button
                type="button"
                onClick={() => setDebug((v) => !v)}
                className="rounded-full border border-seekle-border bg-white px-3 py-1 text-zinc-500 hover:text-zinc-700"
              >
                {debug ? "Hide debug" : "Show debug"}
              </button>
            </div>
          ) : null}

          <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} sessionId={sessionId} />
        </div>
      </div>
    </main>
  );
}
