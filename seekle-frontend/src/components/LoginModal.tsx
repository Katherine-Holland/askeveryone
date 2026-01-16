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
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">(
    "idle"
  );
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
        className="absolute inset-0 bg-[color:var(--color-foreground)]/40"
      />

      {/* modal */}
      <div className="relative w-full max-w-md rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] p-5 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-[color:var(--color-foreground)]">
              Sign Up
            </h2>
            <p className="mt-1 text-sm text-[color:var(--seekle-brown)]">
              Create a free account and save your conversations.
            </p>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-sm text-[color:var(--seekle-brown)] hover:bg-[color:var(--surface-muted)]"
          >
            ✕
          </button>
        </div>

        <form onSubmit={onSubmit} className="mt-4 space-y-3">
          <div className="seekle-input-wrap">
            <div className="seekle-input-glow" />
            <div className="seekle-input-sheen" />

            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="w-full rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] px-4 py-3 text-sm text-[color:var(--color-foreground)] placeholder:text-[color:var(--seekle-brown)]/70 outline-none focus:border-[color:var(--color-seekle-brown)]"
            />
          </div>

          <button
            type="submit"
            disabled={status === "sending"}
            className="w-full rounded-xl bg-[color:var(--color-seekle-brown)] px-4 py-3 text-sm font-medium text-[color:var(--color-background)] shadow-sm transition-colors hover:bg-[color:var(--color-seekle-brown-hover)] disabled:opacity-60"
          >
            {status === "sending" ? "Sending…" : "Email me a login link"}
          </button>

          {status === "sent" ? (
            <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-muted)] p-3 text-sm text-[color:var(--color-foreground)]">
              <span className="font-medium">Link sent.</span> Check your inbox.
            </div>
          ) : null}

          {error ? (
            <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-muted)] p-3 text-sm text-[color:var(--color-foreground)] whitespace-pre-wrap">
              <span className="font-medium">Couldn’t send link:</span> {error}
            </div>
          ) : null}

          <div className="text-xs text-[color:var(--seekle-brown)]">
            Tip: open the link on this device to attach your current session.
          </div>
        </form>
      </div>
    </div>
  );
}
