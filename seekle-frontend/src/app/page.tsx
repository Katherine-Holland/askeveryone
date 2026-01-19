"use client";

import { useEffect, useMemo, useState } from "react";
import { askBackend, isPaywallError, type AskResponse } from "@/lib/api";
import LoginModal from "@/components/LoginModal";
import AccountMenu from "@/components/AccountMenu";
import SeekleRipple from "@/components/SeekleRipple";
import ChatSidebar, { type SidebarItem } from "@/components/ChatSidebar";

function getOrCreateSessionId(): string {
  const key = "seekle_session_id";

  // ✅ guard for SSR/edge hydration
  if (typeof window === "undefined") return "";

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

  if (typeof window === "undefined") return "";

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

// --- Billing (for credits badge) ---
type BillingStatus = {
  ok: boolean;
  user_id: string;
  plan: "free" | "paid" | string;
  tier?: string | null;
  credits_balance: number;
};

async function fetchBillingStatus(
  seekleSessionId: string
): Promise<BillingStatus | null> {
  try {
    const r = await fetch(
      `/api/billing/status?session_id=${encodeURIComponent(seekleSessionId)}`,
      { method: "GET", cache: "no-store" }
    );
    if (!r.ok) return null;
    const data = (await r.json()) as BillingStatus;
    return data;
  } catch {
    return null;
  }
}

// localStorage keys
const LS_THREADS = "seekle_threads_v1";
const LS_ACTIVE = "seekle_threads_active_v1";

function loadThreads(): SavedThread[] {
  try {
    if (typeof window === "undefined") return [];
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
    if (typeof window === "undefined") return;
    localStorage.setItem(LS_THREADS, JSON.stringify(threads.slice(0, 80)));
  } catch {}
}

function loadActiveId(): string | null {
  try {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(LS_ACTIVE);
  } catch {
    return null;
  }
}

function saveActiveId(id: string | null) {
  try {
    if (typeof window === "undefined") return;
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

// Citation shape (backend returns list of {title,url,date})
type Citation = {
  title?: string;
  url?: string;
  date?: string;
};

function safeCitations(resp: AskResponse | null): Citation[] {
  if (!resp) return [];
  const anyResp = resp as any;
  if (!Array.isArray(anyResp.citations)) return [];
  return anyResp.citations as Citation[];
}

export default function Home() {
  const [mounted, setMounted] = useState(false);

  // ✅ IMPORTANT: set sessionId immediately on first client render
  const [sessionId, setSessionId] = useState<string>(() => getOrCreateSessionId());

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  const [resp, setResp] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [loginOpen, setLoginOpen] = useState(false);

  // Billing badge + toast
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  // Dev-only debug visibility (off by default)
  const [debug, setDebug] = useState(false);
  const canShowDebug = process.env.NODE_ENV === "development";

  // “thought” animation trigger
  const [thoughtKey, setThoughtKey] = useState(0);

  // Sources toggle (collapsible)
  const [sourcesOpen, setSourcesOpen] = useState(false);

  // Sidebar state
  const [showSidebar, setShowSidebar] = useState(false);
  const [threads, setThreads] = useState<SavedThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    if (process.env.NODE_ENV === "development") setDebug(false);

    // if sessionId is still empty for any reason, repair it
    if (!sessionId) {
      const sid = getOrCreateSessionId();
      if (sid) setSessionId(sid);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!mounted) return;
    if (!sessionId) return;

    // hydrate sidebar storage
    const t = loadThreads();
    const a = loadActiveId();
    setThreads(t);
    setActiveThreadId(a);

    // decide if we show sidebar (logged-in only) + pull billing
    void (async () => {
      const ok = await isLoggedIn(sessionId);
      setShowSidebar(ok);

      if (ok) {
        const st = await fetchBillingStatus(sessionId);
        setBilling(st);
      } else {
        setBilling(null);
      }

      // if active thread exists, load it
      if (ok && a) {
        const found = t.find((x) => x.id === a);
        if (found) setResp(found.resp);
      }
    })();
  }, [mounted, sessionId]);

  // auto-close sources on new response/thread
  useEffect(() => {
    setSourcesOpen(false);
  }, [thoughtKey, activeThreadId]);

  const rippleMode = useMemo(() => {
    if (loading) return "thinking";
    if (resp) return "answered";
    return "listening";
  }, [loading, resp]);

  async function runAsk() {
    const q = query.trim();
    if (!q || loading) return;

    // should never be empty now, but keep a safe guard
    if (!sessionId) {
      const sid = getOrCreateSessionId();
      if (!sid) return;
      setSessionId(sid);
    }

    setLoading(true);
    setError(null);

    try {
      const out = await askBackend({ query: q, session_id: sessionId });
      setResp(out);
      setThoughtKey((k) => k + 1);
      setQuery("");

      // refresh credits badge (logged-in only)
      if (showSidebar) {
        const st = await fetchBillingStatus(sessionId);
        setBilling(st);
      }

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

  function onLogin() {
    setLoginOpen(true);
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
    setBilling(null);
    setActiveThreadId(null);
    saveActiveId(null);

    // UX toast
    setToast("Logged out");
    setTimeout(() => setToast(null), 1800);

    window.location.assign("/");
  }

  function onUpgrade() {
    window.location.href = "/pricing";
  }

  async function onManagePlan() {
    try {
      const r = await fetch(
        `/api/billing/portal?session_id=${encodeURIComponent(sessionId)}`,
        { method: "POST" }
      );
      const data = await r.json().catch(() => null);
      if (r.ok && data?.url) {
        window.location.href = data.url;
        return;
      }
    } catch {}
    window.location.href = "/pricing";
  }

  function onSelectThread(id: string) {
    const found = threads.find((t) => t.id === id);
    if (!found) return;
    setActiveThreadId(id);
    saveActiveId(id);

    setResp(found.resp);
    setThoughtKey((k) => k + 1);
    setError(null);
  }

  function onNewThread() {
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

  const usageLabel = billing
    ? `${String(billing.tier || billing.plan || "free")} · Credits: ${
        billing.credits_balance
      }`
    : undefined;

  const citations = safeCitations(resp);
  const sourcesCount = Math.min(citations.length, 8);

  return (
    <main className="min-h-screen bg-seekle-cream text-seekle-text">
      {/* Toast */}
      {toast ? (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50">
          <div className="rounded-full border border-seekle-border bg-white px-4 py-2 text-sm text-zinc-700 shadow-sm">
            {toast}
          </div>
        </div>
      ) : null}

      {/* Fixed top-right account menu */}
      <div className="fixed top-6 right-6 z-50">
        {mounted ? (
          <AccountMenu
            isLoggedIn={!!showSidebar}
            onLogin={onLogin}
            onLogout={onLogout}
            onUpgrade={onUpgrade}
            onManagePlan={onManagePlan}
            usageLabel={usageLabel}
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
                credits={billing?.credits_balance ?? null}
                planLabel={
                  billing?.tier
                    ? billing.tier.charAt(0).toUpperCase() +
                      billing.tier.slice(1)
                    : billing?.plan === "paid"
                    ? "Starter"
                    : "Free"
                }
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

                    <div className="relative z-10 flex gap-2 items-end">
                      <div className="relative flex-1">
                        <textarea
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          placeholder="type here... Seekle asks ChatGPT, Perplexity, Claude, Gemini or Grok"
                          rows={1}
                          className="w-full resize-none rounded-2xl border border-seekle-border bg-white px-5 py-3 pr-12 text-base outline-none leading-6 min-h-[52px] max-h-[180px] overflow-y-auto"
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                              e.preventDefault();
                              void runAsk();
                            }
                          }}
                        />

                        {query.trim().length > 0 ? (
                          <button
                            type="button"
                            aria-label="Clear"
                            onClick={() => setQuery("")}
                            className="absolute right-3 top-3 rounded-full border border-zinc-200 bg-white px-2 py-1 text-xs text-zinc-600 hover:bg-zinc-50"
                          >
                            X
                          </button>
                        ) : null}
                      </div>

                      <button
                        type="button"
                        onClick={() => void runAsk()}
                        // ✅ do NOT gate on sessionId
                        disabled={loading || !query.trim()}
                        className="relative z-20 rounded-2xl px-5 py-3 border border-transparent bg-seekle-brown text-white hover:bg-seekle-brownHover disabled:opacity-60 disabled:hover:bg-seekle-brown min-h-[52px]"
                      >
                        {loading ? "Asking" : "Ask"}
                      </button>
                    </div>
                  </div>

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

                        {/* Sources (collapsible) */}
                        {sourcesCount > 0 ? (
                          <div className="mt-5">
                            <button
                              type="button"
                              onClick={() => setSourcesOpen((v) => !v)}
                              className="w-full flex items-center justify-between rounded-xl border border-seekle-border bg-seekle-muted px-3 py-2 hover:bg-white transition-colors"
                              aria-expanded={sourcesOpen}
                            >
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-medium text-seekle-brown">
                                  Sources ({sourcesCount})
                                </span>
                                <span className="text-[11px] text-zinc-500">
                                  {sourcesOpen ? "Hide" : "Show"}
                                </span>
                              </div>

                              <span className="text-seekle-brown text-sm">
                                {sourcesOpen ? "▾" : "▸"}
                              </span>
                            </button>

                            {sourcesOpen ? (
                              <div className="mt-2 space-y-2">
                                {citations.slice(0, 8).map((c, idx) => {
                                  const title = (c?.title || c?.url || "Source").toString();
                                  const url = (c?.url || "").toString();
                                  const date = (c?.date || "").toString();

                                  return (
                                    <a
                                      key={`${url}-${idx}`}
                                      href={url || "#"}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="block rounded-xl border border-seekle-border bg-white px-3 py-2 hover:bg-seekle-muted transition-colors"
                                    >
                                      <div className="text-sm text-seekle-text line-clamp-2">
                                        {idx + 1}. {title}
                                      </div>
                                      <div className="mt-0.5 flex flex-wrap gap-x-2 gap-y-1 text-xs text-zinc-500">
                                        {date ? <span>{date}</span> : null}
                                        {url ? (
                                          <span className="truncate max-w-[520px] underline underline-offset-2">
                                            {url}
                                          </span>
                                        ) : null}
                                      </div>
                                    </a>
                                  );
                                })}
                              </div>
                            ) : null}
                          </div>
                        ) : null}
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

                  <LoginModal
                    open={loginOpen}
                    onClose={() => setLoginOpen(false)}
                    sessionId={sessionId}
                  />

                  <div className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-zinc-500">
                    <a className="hover:text-zinc-700" href="/privacy-policy">
                      Privacy Policy
                    </a>
                    <a className="hover:text-zinc-700" href="/terms">
                      Terms
                    </a>
                    <a className="hover:text-zinc-700" href="/ai-policy">
                      LLM Compliance Policy
                    </a>
                    <a className="hover:text-zinc-700" href="/contact">
                      Contact
                    </a>
                    <a className="hover:text-zinc-700" href="/about">
                      About
                    </a>
                  </div>
                </div>
              </div>
            </div>
            {/* end main column */}
          </div>
        </div>
      </div>
    </main>
  );
}
