// seekle-frontend/src/app/shop/components/ShopResults.tsx
"use client";

import type { ShopPrefs } from "./ShopPreferences";

export type ShopProduct = {
  id: string;
  title: string;
  price: string;
  merchant: string;
  imageUrl: string;
  href: string;
  badges?: string[];
};

function safeImg(src?: string) {
  if (!src || typeof src !== "string") return "/window.svg";
  return src.trim() || "/window.svg";
}

export default function ShopResults({
  mode,
  query,
  prefs,
  activeVibeName,
  products,
  onPin,
  onRemovePin,
  pinnedIds,
  isSearching,
}: {
  mode: "search" | "vibe";
  query: string;
  prefs: ShopPrefs;
  activeVibeName: string;
  products: ShopProduct[];
  onPin: (p: ShopProduct) => void;
  onRemovePin: (productId: string) => void;
  pinnedIds: Set<string>;
  isSearching: boolean;
}) {
  const hasQuery = Boolean(query.trim());
  const hasCountry = Boolean(prefs.country);

  // ✅ 6 at a time
  const visible = products.slice(0, 6);

  const title = mode === "vibe" ? "Vibe Board" : "Results";
  const subtitle =
    mode === "vibe"
      ? `Browsing saved items in ${activeVibeName}`
      : `Saving into ${activeVibeName}`;

  return (
    <section className="rounded-2xl border border-black/10 bg-white p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">{title}</h2>
          <p className="text-xs text-black/60">{subtitle}</p>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2">
          {prefs.saleOnly && (
            <span className="rounded-full border border-black/10 bg-black/5 px-2 py-1 text-xs">
              Sale
            </span>
          )}
          {prefs.gender !== "any" && (
            <span className="rounded-full border border-black/10 bg-black/5 px-2 py-1 text-xs">
              {prefs.gender}
            </span>
          )}
          {prefs.size && (
            <span className="rounded-full border border-black/10 bg-black/5 px-2 py-1 text-xs">
              Size {prefs.size}
            </span>
          )}
          {prefs.pricePreset !== "any" && (
            <span className="rounded-full border border-black/10 bg-black/5 px-2 py-1 text-xs">
              {prefs.pricePreset}
            </span>
          )}
          {hasCountry ? (
            <span className="rounded-full border border-black/10 bg-black/5 px-2 py-1 text-xs">
              {prefs.country}
            </span>
          ) : null}
        </div>
      </div>

      {!hasCountry ? (
        <div className="mb-4 rounded-2xl border border-black/10 bg-black/5 p-3 text-sm">
          <div className="font-medium">Set your country for better relevance.</div>
          <div className="text-xs text-black/60">
            (BETA)
          </div>
        </div>
      ) : null}

      {/* Empty states */}
      {mode === "search" && !hasQuery ? (
        <div className="flex min-h-[380px] flex-col items-center justify-center rounded-2xl border border-dashed border-black/15 bg-black/[0.02] p-8 text-center">
          <div className="text-base font-semibold">Start shopping</div>
          <p className="mt-2 max-w-sm text-sm text-black/60">
            Search above to see results. Save favourites into your Vibes.
          </p>
          <p className="mt-4 text-xs text-black/50">
            Try: <span className="font-medium">“red coat in the sale”</span>
          </p>
        </div>
      ) : null}

      {mode === "vibe" && visible.length === 0 ? (
        <div className="flex min-h-[380px] flex-col items-center justify-center rounded-2xl border border-dashed border-black/15 bg-black/[0.02] p-8 text-center">
          <div className="text-base font-semibold">Nothing saved yet</div>
          <p className="mt-2 max-w-sm text-sm text-black/60">
            Run a search, then tap <span className="font-medium">Save</span> on items you like.
          </p>
        </div>
      ) : null}

      {/* Loading skeleton */}
      {isSearching ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="overflow-hidden rounded-2xl border border-black/10 bg-white">
              <div className="aspect-[4/5] w-full animate-pulse bg-black/[0.06]" />
              <div className="p-4">
                <div className="h-4 w-3/4 rounded bg-black/[0.08] animate-pulse" />
                <div className="mt-2 h-3 w-1/2 rounded bg-black/[0.06] animate-pulse" />
                <div className="mt-4 h-9 w-full rounded-xl bg-black/[0.06] animate-pulse" />
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {/* Premium lookbook grid */}
      {!isSearching && visible.length > 0 ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {visible.map((p) => {
              const isPinned = pinnedIds.has(p.id);

              return (
                <article
                  key={p.id}
                  className="group overflow-hidden rounded-2xl border border-black/10 bg-white"
                >
                  {/* Image */}
                  <a
                    href={p.href || "#"}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="block"
                    title="Open retailer in a new tab"
                  >
                    <div className="relative aspect-[4/5] w-full bg-black/[0.04]">
                      <img
                        src={safeImg(p.imageUrl)}
                        alt={p.title}
                        className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                        loading="lazy"
                      />

                      {/* Overlay badge area (optional) */}
                      {p.badges?.length ? (
                        <div className="absolute left-3 top-3 flex flex-wrap gap-2">
                          {p.badges.slice(0, 2).map((b) => (
                            <span
                              key={b}
                              className="rounded-full border border-black/10 bg-white/90 px-2 py-1 text-xs backdrop-blur"
                            >
                              {b}
                            </span>
                          ))}
                        </div>
                      ) : null}

                      {/* Subtle gradient */}
                      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/15 via-transparent to-transparent" />
                    </div>
                  </a>

                  {/* Meta */}
                  <div className="p-4">
                    <div className="min-w-0">
                      <div className="line-clamp-2 text-sm font-semibold leading-5">
                        {p.title}
                      </div>
                      <div className="mt-1 text-xs text-black/60 line-clamp-1">
                        {p.merchant}
                      </div>

                      {/* No price shown (by design) */}
                      <div className="mt-2 text-xs text-black/50">
                        Seekle BETA
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="mt-4 flex items-center gap-2">
                      <a
                        href={p.href || "#"}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="flex-1 rounded-xl border border-black/10 bg-white px-3 py-2 text-center text-sm hover:bg-black/5"
                      >
                        View
                      </a>

                      {isPinned ? (
                        <button
                          type="button"
                          onClick={() => onRemovePin(p.id)}
                          className="rounded-xl border border-black/10 bg-white px-3 py-2 text-sm hover:bg-black/5"
                          title={`Remove from ${activeVibeName}`}
                        >
                          Remove
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => onPin(p)}
                          className="rounded-xl border border-black/10 bg-black px-3 py-2 text-sm text-white hover:opacity-90"
                          title={`Save to ${activeVibeName}`}
                        >
                          ♡ Save
                        </button>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="mt-4 text-xs text-black/50">
            Showing 6 {mode === "vibe" ? "saved items" : "results"}.
          </div>
        </>
      ) : null}

      {/* If search has a query but no results */}
      {!isSearching && mode === "search" && hasQuery && products.length === 0 ? (
        <div className="flex min-h-[340px] flex-col items-center justify-center rounded-2xl border border-dashed border-black/15 bg-black/[0.02] p-8 text-center">
          <div className="text-base font-semibold">No results yet</div>
          <p className="mt-2 max-w-sm text-sm text-black/60">
            Try a broader search. (BETA)
          </p>
        </div>
      ) : null}
    </section>
  );
}
