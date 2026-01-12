"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  sessionId: string;
  onLogout: () => void;
  onUpgrade?: () => void;
  usageLabel?: string; // placeholder for now
};

export default function AccountMenu({ sessionId, onLogout, onUpgrade, usageLabel }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, []);

  const short = sessionId ? `${sessionId.slice(0, 8)}…` : "—";

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        Account
      </button>

      {open ? (
        <div className="absolute right-0 mt-2 w-56 rounded-xl border border-zinc-200 bg-white shadow-lg overflow-hidden">
          <div className="px-4 py-3 text-xs text-zinc-500">
            <div className="font-medium text-zinc-700">Signed in (session)</div>
            <div className="mt-1 select-all">Session: {short}</div>
            {usageLabel ? <div className="mt-2">{usageLabel}</div> : null}
          </div>

          <div className="h-px bg-zinc-100" />

          <button
            type="button"
            onClick={() => {
              setOpen(false);
              onUpgrade?.();
            }}
            className="w-full text-left px-4 py-3 text-sm hover:bg-zinc-50"
          >
            Upgrade
          </button>

          <button
            type="button"
            onClick={() => {
              setOpen(false);
              // For now this is just a placeholder. We'll wire real usage soon.
              alert("Usage page coming next (Task: Usage).");
            }}
            className="w-full text-left px-4 py-3 text-sm hover:bg-zinc-50"
          >
            Usage
          </button>

          <div className="h-px bg-zinc-100" />

          <button
            type="button"
            onClick={() => {
              setOpen(false);
              onLogout();
            }}
            className="w-full text-left px-4 py-3 text-sm text-red-600 hover:bg-zinc-50"
          >
            Log out
          </button>
        </div>
      ) : null}
    </div>
  );
}
