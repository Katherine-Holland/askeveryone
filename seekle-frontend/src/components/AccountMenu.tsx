"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  onLogout: () => void;
  onUpgrade?: () => void;
  usageLabel?: string; // placeholder for now
  debugSession?: string | null; // only pass in dev if you want
};

export default function AccountMenu({ onLogout, onUpgrade, usageLabel, debugSession }: Props) {
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
            <div className="font-medium text-zinc-700">Account</div>
            {usageLabel ? <div className="mt-2">{usageLabel}</div> : null}

            {/* Dev-only debug (only shows if you pass debugSession) */}
            {debugSession ? (
              <div className="mt-2 rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2">
                <div className="text-[11px] text-zinc-500">Debug session:</div>
                <div className="mt-1 text-[11px] text-zinc-700 select-all break-all">
                  {debugSession}
                </div>
              </div>
            ) : null}
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
              alert("Usage page coming next.");
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
