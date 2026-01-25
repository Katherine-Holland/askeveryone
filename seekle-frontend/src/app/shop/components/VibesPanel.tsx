// seekle-frontend/src/app/shop/components/VibesPanel.tsx
"use client";

export type Vibe = {
  id: string;
  name: string;
  description: string;
  isStarter?: boolean;
  // Later: public/private, share slug, etc.
};

type Thumb = {
  id: string;
  imageUrl: string;
  title?: string;
};

export default function VibesPanel({
  vibes,
  activeVibeId,
  onSelectVibe,
  onCreateVibe,
  onShareVibe,
  countsByVibeId,
  thumbsByVibeId,
}: {
  vibes: Vibe[];
  activeVibeId: string;
  onSelectVibe: (id: string) => void;
  onCreateVibe: () => void;
  onShareVibe: (vibeId: string) => void;
  countsByVibeId?: Record<string, number>;
  thumbsByVibeId?: Record<string, Thumb[]>;
}) {
  return (
    <aside className="rounded-2xl border border-black/10 bg-white p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">Vibes</h2>
          <p className="text-xs text-black/60">
            Save favourites into your vibe. Share later.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onShareVibe(activeVibeId)}
            className="rounded-xl border border-black/10 bg-white px-3 py-2 text-sm hover:bg-black/5"
            title="Share this vibe"
          >
            Share Vibe
          </button>

          <button
            type="button"
            onClick={onCreateVibe}
            className="rounded-xl border border-black/10 bg-white px-3 py-2 text-sm hover:bg-black/5"
          >
            + New
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {vibes.map((v) => {
          const count = countsByVibeId?.[v.id] ?? 0;
          const thumbs = thumbsByVibeId?.[v.id] ?? [];
          const top = thumbs.slice(0, 3);
          const overflow = Math.max(0, thumbs.length - top.length);

          const isActive = v.id === activeVibeId;

          return (
            <button
              key={v.id}
              type="button"
              onClick={() => onSelectVibe(v.id)}
              className={[
                "w-full rounded-2xl border p-3 text-left transition",
                isActive
                  ? "border-black/20 bg-black/5"
                  : "border-black/10 bg-white hover:bg-black/5",
              ].join(" ")}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-sm font-medium">{v.name}</div>
                  <div className="mt-1 text-xs text-black/60">
                    {v.description}
                  </div>
                </div>

                <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-black/10 bg-white px-2 py-0.5 text-xs text-black/70">
                  <span className="font-medium">{count}</span>
                  <span className="text-black/50">saved</span>
                </span>
              </div>

              {/* Thumbnail strip */}
              <div className="mt-3 flex items-center gap-2">
                {top.length > 0 ? (
                  <>
                    {top.map((t) => (
                      <div
                        key={t.id}
                        className="h-9 w-9 overflow-hidden rounded-xl border border-black/10 bg-white"
                        title={t.title || "Saved item"}
                      >
                        <img
                          src={t.imageUrl || "/window.svg"}
                          alt=""
                          className="h-full w-full object-contain p-1"
                          loading="lazy"
                        />
                      </div>
                    ))}

                    {overflow > 0 ? (
                      <div className="flex h-9 items-center rounded-xl border border-black/10 bg-white px-2 text-xs text-black/60">
                        +{overflow}
                      </div>
                    ) : null}
                  </>
                ) : (
                  <div className="text-xs text-black/50">
                    {v.isStarter
                      ? "Start shopping to add items here."
                      : "No saved items yet."}
                  </div>
                )}
              </div>

              <div className="mt-3 text-xs text-black/50">
                (BETA.)
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
