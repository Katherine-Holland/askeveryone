"use client";

import { type ShopPrefs } from "./ShopPreferences";

export type ShopProduct = {
  id: string;
  title: string;
  price: string; // still present from API, but we won't display it
  merchant: string;
  imageUrl: string;
  href: string;
  badges?: string[];
};

export default function ShopResults({
  query,
  prefs,
  activeVibeName,
  products,
  onPin,
  isSearching,
}: {
  query: string;
  prefs: ShopPrefs;
  activeVibeName: string;
  products: ShopProduct[];
  onPin: (p: ShopProduct) => void;
  isSearching: boolean;
}) {
  const hasQuery = Boolean(query.trim());
  const hasCountry = Boolean(prefs.country);

  // ✅ 6 results per page
  const visible = products.slice(0, 6);

  return (
    <section className="rounded-2xl border border-black/10 bg-white p-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Lookbook</h2>
          <p className="text-xs text-black/60">
            Vibe: <span className="font-medium">{activeVibeName}</span>
            {prefs.country ? (
              <>
                {" "}
                · Country: <span className="font-medium">{prefs.country}</span>
              </>
            ) : null}
          </p>
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
        </div>
      </div>

      {isSearching ? (
        <div className="grid grid-cols-2 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="overflow-hidden rounded-2xl border border-black/10 bg-white"
            >
              <div className="aspect-[3/4] w-full animate-pulse bg-black/[0.06]" />
              <div className="p-4">
                <div className="h-4 w-4/5 animate-pulse rounded bg-black/[0.08]" />
                <div className="mt-2 h-3 w-2/5 animate-pulse rounded bg-black/[0.06]" />
                <div className="mt-4 h-9 w-full animate-pulse rounded-xl bg-black/[0.06]" />
              </div>
            </div>
          ))}
        </div>
      ) : !hasQuery ? (
        <div className="flex min-h-[440px] flex-col items-center justify-center rounded-2xl border border-dashed border-black/15 bg-black/[0.02] p-10 text-center">
          <div className="text-base font-semibold">Start browsing</div>
          <p className="mt-2 max-w-sm text-sm text-black/60">
            Search above — you’ll get 6 visual picks at a time. Save what fits the vibe.
          </p>
          <p className="mt-4 text-xs text-black/50">
            Try: <span className="font-medium">“red coat in the sale”</span>
          </p>
        </div>
      ) : !hasCountry ? (
        <div className="mb-4 rounded-2xl border border-black/10 bg-black/5 p-3 text-sm">
          <div className="font-medium">Set your country for better relevance.</div>
          <div className="text-xs text-black/60">(BETA: we’ll refine region signals over time.)</div>
        </div>
      ) : visible.length === 0 ? (
        <div className="flex min-h-[440px] flex-col items-center justify-center rounded-2xl border border-dashed border-black/15 bg-black/[0.02] p-10 text-center">
          <div className="text-base font-semibold">No results</div>
          <p className="mt-2 max-w-sm text-sm text-black/60">
            Try a broader search. We’ll improve matching over time.
          </p>
        </div>
      ) : (
        <>
          {/* ✅ Premium lookbook grid (2 columns, big visuals) */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {visible.map((p) => (
              <article
                key={p.id}
                className="group overflow-hidden rounded-2xl border border-black/10 bg-white transition-all duration-200 hover:-translate-y-[1px] hover:shadow-lg"
              >
                <a
                  href={p.href || "#"}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="block"
                  title="Open retailer in a new tab"
                >
                  <div className="relative aspect-[3/4] w-full bg-black/[0.04]">
                    <img
                      src={p.imageUrl || "/window.svg"}
                      alt={p.title}
                      className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                      loading="lazy"
                    />

                    {/* soft overlay on hover */}
                    <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                      <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-black/0 to-black/0" />
                    </div>

                    {/* Seekle micro mark */}
                    <div className="absolute bottom-3 right-3 rounded-full border border-white/30 bg-black/30 px-2 py-1 text-[11px] text-white backdrop-blur">
                      seekle
                    </div>

                    {/* Badges (optional) */}
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
                  </div>
                </a>

                <div className="p-4">
                  <div className="min-w-0">
                    <div className="line-clamp-2 text-sm font-semibold leading-5">
                      {p.title}
                    </div>
                    <div className="mt-1 line-clamp-1 text-xs text-black/60">
                      {p.merchant}
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

                    <button
                      type="button"
                      onClick={() => onPin(p)}
                      className="rounded-xl border border-black/10 bg-black px-3 py-2 text-sm text-white hover:opacity-90"
                      title={`Save to ${activeVibeName}`}
                    >
                      ♡ Save
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>

          <div className="mt-4 text-xs text-black/50">
            Showing 6 results (visual-first, BETA).
          </div>
        </>
      )}
    </section>
  );
}
