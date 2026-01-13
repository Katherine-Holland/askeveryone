"use client";

import { useEffect, useState } from "react";

export default function UpgradeEmailModal({
  open,
  onClose,
  onSuccess,
}: {
  open: boolean;
  onClose: () => void;
  onSuccess: (email: string) => void;
}) {
  const [email, setEmail] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setErr(null);
      setEmail("");
    }
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="text-lg font-semibold">Continue to checkout</div>
        <p className="mt-2 text-sm text-zinc-600">
          Enter your email so we can attach your subscription to your account.
        </p>

        {err ? (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {err}
          </div>
        ) : null}

        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@company.com"
          className="mt-4 w-full rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-black/10"
        />

        <div className="mt-5 flex gap-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-full border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-700 hover:bg-zinc-100"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => {
              const e = email.trim().toLowerCase();
              if (!e || !e.includes("@")) {
                setErr("Please enter a valid email address.");
                return;
              }
              onSuccess(e);
            }}
            className="flex-1 rounded-full border bg-black px-4 py-3 text-sm text-white"
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}
