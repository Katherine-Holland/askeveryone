"use client";

import { useState } from "react";
import { requestMagicLink } from "@/lib/api";

export default function LoginModal(props: {
  open: boolean;
  onClose: () => void;
  sessionId: string;
}) {
  const { open, onClose, sessionId } = props;
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const clean = email.trim().toLowerCase();
    if (!clean || !clean.includes("@")) {
      setError("Enter a valid email.");
      return;
    }

    setStatus("sending");
    try {
      await requestMagicLink({ email: clean, session_id: sessionId });
      setStatus("sent");
    } catch (err: any) {
      setStatus("error");
      setError(err?.message || "Could not send link.");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* overlay */}
      <button
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0 bg-black/40"
      />

      {/* modal */}
      <div className="relative w-full max-w-md rounded-2xl border bg-white p-5 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Save your conversation</h2>
            <p className="mt-1 text-sm text-zinc-600">
              Create a free account to keep chatting and pick up where you left off.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-sm text-zinc-500 hover:bg-zinc-100"
          >
            ✕
          </button>
        </div>

        <form onSubmit={onSubmit} className="mt-4 space-y-3">
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            className="w-full rounded-xl border px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-black/10"
          />

          <button
            type="submit"
            disabled={status === "sending"}
            className="w-full rounded-xl bg-black px-4 py-3 text-sm font-medium text-white disabled:opacity-50"
          >
            {status === "sending" ? "Sending…" : "Email me a login link"}
          </button>

          {status === "sent" ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
              Link sent. Check your inbox.
            </div>
          ) : null}

          {error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 whitespace-pre-wrap">
              {error}
            </div>
          ) : null}

          <div className="text-xs text-zinc-500">
            Tip: open the link on this device to attach your current session.
          </div>
        </form>
      </div>
    </div>
  );
}
