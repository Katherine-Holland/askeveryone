"use client";

import { useEffect, useMemo, useState } from "react";
import { askBackend, isPaywallError, type AskResponse } from "@/lib/api";
import LoginModal from "@/components/LoginModal";
import AccountMenu from "@/components/AccountMenu";
import SeekleRipple from "@/components/SeekleRipple";
import ChatSidebar, { type SidebarItem } from "@/components/ChatSidebar";

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

type SavedThread = {
  id: string;
  title: string;
  createdAt: number;
  resp: AskResponse;
};

// localStorage keys
const LS_THREADS = "seekle_threads_v1";
const LS_ACTIVE = "seekle_threads_active_v1";

function loadThreads(): SavedThread[] {
  try {
    const raw = localStorage.getItem(LS_THREADS);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as SavedThread[]) : [];
  } catch {
    return [];
  }
}

function saveThreads(threads: SavedThread[]) {
  try {
    localStorage.setItem(LS_THREADS, JSON.stringify(threads.slice(0, 80)));
  } catch {}
}

function loadActiveId(): string | null {
  try {
    return localStorage.getItem(LS_ACTIVE);
  } catch {
    return null;
  }
}

function saveActiveId(id: string | null) {
  try {
    if (!id) localStorage.removeItem(LS_ACTIVE);
    else localStorage.setItem(LS_ACTIVE, id);
  } catch {}
}

async function isLoggedIn(seekleSessionId: string): Promise<boolean> {
  try {
    const r = await fetch(
      `/api/billing/status?session_id=${encodeURIComponent(seekleSessionId)}`,
      { method: "GET", cache: "no-store" }
    );
    return r.ok;
  } catch {
    return false;
  }
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
  const canShowDebug = process.env.NODE_ENV === "development";

  // “thought” animation trigger
  const [thoughtKey, setThoughtKey] = useState(0);

  // Sidebar state
  const [showSidebar, setShowSidebar] = useState(false);
  const [threads, setThreads] = useState<SavedThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    const sid = getOrCreateSessionId();
    setSessionId(sid);
    if (process.env.NODE_ENV === "development") setDebug(false);

    // hydrate sidebar storage
    const t = loadThreads();
    const a = loadActiveId();
    setThreads(t);
    setActiveThreadId(a);

    // decide if we show sidebar (logged-in only)
    void (async () => {
      const ok = await isLoggedIn(sid);
      setShowSidebar(ok);
      // if active thread exists, load it
      if (ok && a) {
        const found = t.find((x) => x.id === a);
        if (found) setResp(found.resp);
      }
    })();
  }, []);

  const rippleMode = useMemo(() => {
    if (loading) return "thinking";
    if (resp) return "answered";
    return "listening";
  }, [loading, resp]);

  async function runAsk() {
    const q = query.trim();
    if (!q || !sessionId || loading) return;

    setLoading(true);
    setError(null);

    try {
      const out = await askBackend({ query: q, session_id: sessionId });
      setResp(out);
      setThoughtKey((k) => k + 1);
      setQuery("");

      // If logged in, save to sidebar as a “thread”
      if (showSidebar) {
        const title = q.length > 60 ? q.slice(0, 57) + "…" : q;
        const id =
          typeof crypto !== "undefined" && "randomUUID" in crypto
            ? crypto.randomUUID()
            : `${Date.now()}-${Math.random()}`;

        const next: SavedThread[] = [
          { id, title, createdAt: Date.now(), resp: out },
          ...threads,
        ].slice(0, 80);

        setThreads(next);
        saveThreads(next);

        setActiveThreadId(id);
        saveActiveId(id);
      }
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

    // reset session id
    const newId = resetSessionId();
    setSessionId(newId);

    // sidebar off for anon
    setShowSidebar(false);
    setActiveThreadId(null);
    saveActiveId(null);

    window.location.assign("/");
  }

  function onUpgrade() {
    window.location.href = "/pricing";
  }

  function onSelectThread(id: string) {
    const found = threads.find((t) => t.id === id);
    if (!found) return;
    setActiveThreadId(id);
    saveActiveId(id);

    // Replace answer in place (no “scrolling chat”)
    setResp(found.resp);
    setThoughtKey((k) => k + 1);
    setError(null);
  }

  function onNewThread() {
    // “New” just clears the current answer area
    setActiveThreadId(null);
    saveActiveId(null);
    setResp(null);
    setError(null);
    setQuery("");
    setThoughtKey((k) => k + 1);
  }

  const sidebarItems: SidebarItem[] = useMemo(
    () =>
      threads.map((t) => ({
        id: t.id,
        title: t.title,
        createdAt: t.createdAt,
      })),
    [threads]
  );

  return (
    <main className="min-h-screen bg-seekle-cream text-seekle-text">
      {/* Fixed top-right account menu */}
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

      <div className="min-h-screen p-6">
        <div className="mx-auto max-w-6xl">
          <div className="flex gap-6 items-start">
            {/* Left sidebar (logged-in only) */}
            {mounted && showSidebar ? (
              <ChatSidebar
                items={sidebarItems}
                activeId={activeThreadId}
                onSelect={onSelectThread}
                onNew={onNewThread}
              />
            ) : null}

            {/* Main column */}
            <div className="flex-1">
              <div className="min-h-[88vh] flex items-center justify-center">
                <div className="w-full max-w-2xl">
                  <div className="text-center mb-8">
                    <h1 className="text-5xl font-semibold tracking-tight">
                      Seekle
                    </h1>
                    <p className="mt-3 text-sm text-zinc-600">Ask Everyone.</p>
                  </div>

                  {/* Input halo wrapper */}
                  <div
                    className="seekle-input-wrap"
                    data-loading={loading ? "true" : "false"}
                  >
                    <div className="seekle-input-glow" />
                    <div className="seekle-input-sheen" />

                    <div className="flex gap-2 items-center relative">
                      <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Ask or type..."
                        className="flex-1 rounded-full border border-seekle-border bg-white px-5 py-3 text-base outline-none"
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
                        className="rounded-full px-5 py-3 border border-transparent bg-seekle-brown text-white hover:bg-seekle-brown-hover disabled:opacity-50"
                      >
                        {loading ? "…" : "Search"}
                      </button>
                    </div>
                  </div>

                  {/* Ripple always present */}
                  <SeekleRipple mode={rippleMode} size={110} />

                  <div className="mt-8 space-y-3">
                    {error ? (
                      <div className="rounded-xl border border-red-200 bg-white p-4 text-sm text-red-600 whitespace-pre-wrap">
                        {error}
                      </div>
                    ) : null}

                    {resp ? (
                      <div
                        key={thoughtKey}
                        className="rounded-2xl border border-seekle-border bg-white p-5 seekle-thought-in seekle-thought-sheen"
                      >
                        <div className="text-xs text-zinc-500 mb-2">
                          Provider: {resp.provider_used} · Intent: {resp.intent}
                        </div>
                        <div className="whitespace-pre-wrap leading-7">
                          {resp.answer}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  {/* Dev-only debug toggle */}
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

                  <LoginModal
                    open={loginOpen}
                    onClose={() => setLoginOpen(false)}
                    sessionId={sessionId}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
