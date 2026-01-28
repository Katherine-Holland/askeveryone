// seekle-frontend/src/app/shop/components/ShopResults.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
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
  onShuffleVibe,
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
  onShuffleVibe: () => void;
}) {
  const hasQuery = Boolean(query.trim());
  const hasCountry = Boolean(prefs.country);

  // ✅ 6 at a time
  const PAGE_SIZE = 6;
  const totalPages = Math.max(1, Math.ceil(products.length / PAGE_SIZE));

  const [page, setPage] = useState(0);

  // Reset page when mode/query/products change
  useEffect(() => {
    setPage(0);
  }, [mode, query, products.length]);

  const visible = useMemo(() => {
    const start = page * PAGE_SIZE;
    return products.slice(start, start + PAGE_SIZE);
  }, [products, page]);

  const title = mode === "vibe" ? "Vibe Board" : "Results";
  const subtitle =
    mode === "vibe"
      ? `Browsing saved items in ${activeVibeName}`
      : `Saving into ${activeVibeName}`;

  const canPrev = page > 0;
  const canNext = page < totalPages - 1;

  return (
    <section className="rounded-2xl border border-black/10 bg-white p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">{title}</h2>
          <p className="text-xs text-black/60">{subtitle}</p>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2">
          {mode === "vibe" ? (
            <button
              type="button"
              onClick={onShuffleVibe}
              className="rounded-xl border border-black/10 bg-white px-3 py-2 text-sm hover:bg-black/5"
              title="Shuffle this vibe"
            >
              Shuffle
            </button>
          ) : null}

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
            (BETA: price is bracketed; final price confirmed on retailer site.)
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

      {mode === "vibe" && products.length === 0 ? (
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
                      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/15 via-transparent to-transparent" />
                    </div>
                  </a>

                  <div className="p-4">
                    <div className="min-w-0">
                      <div className="line-clamp-2 text-sm font-semibold leading-5">
                        {p.title}
                      </div>
                      <div className="mt-1 text-xs text-black/60 line-clamp-1">
                        {p.merchant}
                      </div>
                      <div className="mt-2 text-xs text-black/50">
                        Seekle BETA · Price shown on retailer
                      </div>
                    </div>

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

          {/* Pagination: subtle page dots + prev/next */}
          {products.length > PAGE_SIZE ? (
            <div className="mt-4 flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={!canPrev}
                className="rounded-xl border border-black/10 bg-white px-3 py-2 text-sm hover:bg-black/5 disabled:opacity-40"
              >
                ← Prev
              </button>

              <div className="flex items-center gap-2">
                {Array.from({ length: totalPages }).map((_, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setPage(i)}
                    aria-label={`Page ${i + 1}`}
                    className={[
                      "h-2.5 w-2.5 rounded-full border transition",
                      i === page
                        ? "border-black/40 bg-black/30"
                        : "border-black/15 bg-black/5 hover:bg-black/10",
                    ].join(" ")}
                  />
                ))}
              </div>

              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={!canNext}
                className="rounded-xl border border-black/10 bg-white px-3 py-2 text-sm hover:bg-black/5 disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          ) : (
            <div className="mt-4 text-xs text-black/50">Showing 6 items.</div>
          )}
        </>
      ) : null}

      {!isSearching && mode === "search" && hasQuery && products.length === 0 ? (
        <div className="flex min-h-[340px] flex-col items-center justify-center rounded-2xl border border-dashed border-black/15 bg-black/[0.02] p-8 text-center">
          <div className="text-base font-semibold">No results yet</div>
          <p className="mt-2 max-w-sm text-sm text-black/60">
            Try a broader search. (BETA: ranking and filtering will improve.)
          </p>
        </div>
      ) : null}
    </section>
  );
}
