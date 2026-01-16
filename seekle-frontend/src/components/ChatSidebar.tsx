"use client";

import React from "react";

export type SidebarItem = {
  id: string;
  title: string;
  createdAt: number;
};

type Props = {
  items: SidebarItem[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;

  // ✅ New (optional): show credits + plan
  credits?: number | null;
  planLabel?: string | null; // e.g. "Starter" or "Free"
};

export default function ChatSidebar({
  items,
  activeId,
  onSelect,
  onNew,
  credits = null,
  planLabel = null,
}: Props) {
  const creditsText =
    typeof credits === "number" ? `${credits.toLocaleString()} credits` : "…";

  const planText = (planLabel || "").trim() || "Account";

  return (
    <aside className="hidden lg:flex lg:w-72 xl:w-80 shrink-0">
      <div className="w-full rounded-2xl border border-seekle-border bg-white/70 backdrop-blur-sm overflow-hidden">
        <div className="p-4 border-b border-seekle-border flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-sm font-medium text-zinc-800 truncate">
              {planText}
            </div>
            <div className="mt-1 flex items-center gap-2 text-[11px] text-zinc-600">
              <span className="inline-flex items-center rounded-full border border-seekle-border bg-white px-2 py-0.5">
                {creditsText}
              </span>
              <span className="text-zinc-400">·</span>
              <span className="text-zinc-500">Saved questions</span>
            </div>
          </div>

          <button
            type="button"
            onClick={onNew}
            className="shrink-0 rounded-full px-3 py-1 text-xs border border-seekle-border bg-white hover:bg-zinc-50 text-zinc-700"
          >
            New
          </button>
        </div>

        <div className="p-2 max-h-[72vh] overflow-auto">
          {items.length === 0 ? (
            <div className="p-3 text-xs text-zinc-500">
              Ask something to start building your list.
            </div>
          ) : (
            <ul className="space-y-1">
              {items.map((it) => {
                const isActive = it.id === activeId;
                return (
                  <li key={it.id}>
                    <button
                      type="button"
                      onClick={() => onSelect(it.id)}
                      className={[
                        "w-full text-left rounded-xl px-3 py-2 border transition",
                        isActive
                          ? "border-seekle-border bg-white shadow-sm"
                          : "border-transparent hover:border-seekle-border hover:bg-white/80",
                      ].join(" ")}
                      title={it.title}
                    >
                      <div className="text-sm text-zinc-800 line-clamp-2">
                        {it.title}
                      </div>
                      <div className="mt-1 text-[11px] text-zinc-500">
                        {new Date(it.createdAt).toLocaleString()}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="p-3 border-t border-seekle-border text-[11px] text-zinc-500">
          Only the latest answer shows on the right — older ones live here.
        </div>
      </div>
    </aside>
  );
}
