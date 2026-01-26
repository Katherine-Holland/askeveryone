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

function safeImg(src?: string) {
  if (!src || typeof src !== "string") return "/window.svg";
  return src.trim() || "/window.svg";
}

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

      <div className="space-y-3">
        {vibes.map((v) => {
          const count = countsByVibeId?.[v.id] ?? 0;
          const thumbs = thumbsByVibeId?.[v.id] ?? [];

          // Newest-first is already what your pinning does; treat thumbs[0] as cover.
          const cover = thumbs[0];
          const grid = thumbs.slice(0, 4);

          const isActive = v.id === activeVibeId;

          return (
            <button
              key={v.id}
              type="button"
              onClick={() => onSelectVibe(v.id)}
              className={[
                "w-full overflow-hidden rounded-2xl border text-left transition",
                "hover:shadow-sm",
                isActive
                  ? "border-black/20 bg-black/[0.02]"
                  : "border-black/10 bg-white hover:bg-black/[0.02]",
              ].join(" ")}
            >
              {/* Visual preview */}
              <div className="relative">
                {/* Big cover */}
                <div className="relative aspect-[16/10] w-full bg-black/[0.04]">
                  <img
                    src={safeImg(cover?.imageUrl)}
                    alt=""
                    className={[
                      "h-full w-full object-cover",
                      cover?.imageUrl ? "" : "opacity-60",
                    ].join(" ")}
                    loading="lazy"
                  />

                  {/* Top overlays */}
                  <div className="absolute left-3 top-3">
                    <span className="rounded-full border border-black/10 bg-white/90 px-2 py-1 text-xs backdrop-blur">
                      {v.name}
                    </span>
                  </div>

                  <div className="absolute right-3 top-3">
                    <span className="inline-flex items-center gap-1 rounded-full border border-black/10 bg-white/90 px-2 py-1 text-xs text-black/70 backdrop-blur">
                      <span className="font-medium">{count}</span>
                      <span className="text-black/50">saved</span>
                    </span>
                  </div>

                  {/* Subtle Seekle “lookbook” feel */}
                  <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/10 via-transparent to-transparent" />
                </div>

                {/* Mini board preview */}
                <div className="border-t border-black/10 bg-white p-3">
                  {grid.length > 0 ? (
                    <div className="grid grid-cols-4 gap-2">
                      {grid.map((t) => (
                        <div
                          key={t.id}
                          className="aspect-square overflow-hidden rounded-xl border border-black/10 bg-black/[0.03]"
                          title={t.title || "Saved item"}
                        >
                          <img
                            src={safeImg(t.imageUrl)}
                            alt=""
                            className="h-full w-full object-cover"
                            loading="lazy"
                          />
                        </div>
                      ))}
                      {grid.length < 4
                        ? Array.from({ length: 4 - grid.length }).map((_, i) => (
                            <div
                              key={`empty-${v.id}-${i}`}
                              className="aspect-square overflow-hidden rounded-xl border border-dashed border-black/10 bg-black/[0.02]"
                            />
                          ))
                        : null}
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-dashed border-black/10 bg-black/[0.02] p-3 text-sm text-black/60">
                      {v.isStarter
                        ? "Start shopping to add items to this vibe."
                        : "No saved items yet."}
                    </div>
                  )}

                  {/* Description */}
                  <div className="mt-3">
                    <div className="text-xs text-black/60">{v.description}</div>
                    <div className="mt-2 text-[11px] text-black/45">BETA</div>
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
