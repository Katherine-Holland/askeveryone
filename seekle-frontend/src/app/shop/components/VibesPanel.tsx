// seekle-frontend/src/app/shop/components/VibesPanel.tsx
"use client";

import EmptyVibeCard from "./EmptyVibeCard";

export type Vibe = {
  id: string;
  name: string;
  description: string;
  isStarter?: boolean;
  // Later: thumbnails, pin count, public/private, share slug, etc.
};

export default function VibesPanel({
  vibes,
  activeVibeId,
  onSelectVibe,
  onCreateVibe,
}: {
  vibes: Vibe[];
  activeVibeId: string;
  onSelectVibe: (id: string) => void;
  onCreateVibe: () => void;
}) {
  const hasRealVibes = vibes.some((v) => !v.isStarter);

  return (
    <aside className="rounded-2xl border border-black/10 bg-white p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">Vibes</h2>
          <p className="text-xs text-black/60">Save favourites into a vibe. Share later.</p>
        </div>

        <button
          type="button"
          onClick={onCreateVibe}
          className="rounded-xl border border-black/10 bg-white px-3 py-2 text-sm hover:bg-black/5"
        >
          + New
        </button>
      </div>

      {!hasRealVibes ? (
        <div className="space-y-3">
          {vibes.map((v) => (
            <EmptyVibeCard
              key={v.id}
              title={v.name}
              description={v.description}
              isActive={v.id === activeVibeId}
              onClick={() => onSelectVibe(v.id)}
              ctaLabel="Start shopping"
            />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {vibes.map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => onSelectVibe(v.id)}
              className={[
                "w-full rounded-2xl border p-3 text-left transition",
                v.id === activeVibeId ? "border-black/20 bg-black/5" : "border-black/10 bg-white hover:bg-black/5",
              ].join(" ")}
            >
              <div className="text-sm font-medium">{v.name}</div>
              <div className="mt-1 text-xs text-black/60">{v.description}</div>
              <div className="mt-3 text-xs text-black/50">
                (Pins + share links come in Phase 2 once Neon is wired.)
              </div>
            </button>
          ))}
        </div>
      )}
    </aside>
  );
}
