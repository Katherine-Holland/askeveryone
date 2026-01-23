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

export default function ShopResults({
  query,
  prefs,
  activeVibeName,
  products,
  onPin,
}: {
  query: string;
  prefs: ShopPrefs;
  activeVibeName: string;
  products: ShopProduct[];
  onPin: (p: ShopProduct) => void;
}) {
  const hasQuery = Boolean(query.trim());
  const hasCountry = Boolean(prefs.country);

  return (
    <section className="rounded-2xl border border-black/10 bg-white p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Results</h2>
          <p className="text-xs text-black/60">
            Vibe: <span className="font-medium">{activeVibeName}</span>
            {prefs.country ? (
              <>
                {" "}
                · Country: <span className="font-medium">{prefs.country}</span>
              </>
            ) : (
              ""
            )}
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

      {!hasCountry && (
        <div className="mb-4 rounded-2xl border border-black/10 bg-black/5 p-3 text-sm">
          <div className="font-medium">Set your country for accurate prices & delivery.</div>
          <div className="text-xs text-black/60">
            (Phase 1: this will matter more once Shopify results are live.)
          </div>
        </div>
      )}

      {!hasQuery ? (
        <div className="flex min-h-[340px] flex-col items-center justify-center rounded-2xl border border-dashed border-black/15 bg-black/[0.02] p-8 text-center">
          <div className="text-base font-semibold">Start shopping</div>
          <p className="mt-2 max-w-sm text-sm text-black/60">
            Search for something above. We’ll show purchasable results and you can save favourites to your Vibes.
          </p>
          <p className="mt-4 text-xs text-black/50">
            Try: <span className="font-medium">“red coat in the sale”</span>
          </p>
        </div>
      ) : products.length === 0 ? (
        <div className="flex min-h-[340px] flex-col items-center justify-center rounded-2xl border border-dashed border-black/15 bg-black/[0.02] p-8 text-center">
          <div className="text-base font-semibold">No results yet</div>
          <p className="mt-2 max-w-sm text-sm text-black/60">
            (UI skeleton) Once Shopify is connected, this will show real products.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {products.map((p) => (
            <article key={p.id} className="rounded-2xl border border-black/10 bg-white p-3">
              <div className="flex gap-3">
                <div className="h-16 w-16 flex-none overflow-hidden rounded-xl border border-black/10 bg-black/5">
                  {/* Placeholder image; later replace with <Image /> */}
                  <img src={p.imageUrl} alt="" className="h-full w-full object-contain p-2 opacity-70" />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{p.title}</div>
                      <div className="mt-1 text-xs text-black/60">{p.merchant}</div>
                    </div>
                    <div className="text-sm font-semibold">{p.price}</div>
                  </div>

                  {p.badges?.length ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {p.badges.map((b) => (
                        <span
                          key={b}
                          className="rounded-full border border-black/10 bg-black/5 px-2 py-0.5 text-xs"
                        >
                          {b}
                        </span>
                      ))}
                    </div>
                  ) : null}

                  <div className="mt-3 flex items-center gap-2">
                    <a
                      href={p.href}
                      className="flex-1 rounded-xl border border-black/10 bg-white px-3 py-2 text-center text-sm hover:bg-black/5"
                    >
                      View offer
                    </a>
                    <button
                      type="button"
                      onClick={() => onPin(p)}
                      className="rounded-xl border border-black/10 bg-black px-3 py-2 text-sm text-white hover:opacity-90"
                      title={`Save to ${activeVibeName}`}
                    >
                      Save
                    </button>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {hasQuery && (
        <div className="mt-4 text-xs text-black/50">
          Phase 1 note: results are placeholder cards. Next step is wiring Shopify search → real cards.
        </div>
      )}
    </section>
  );
}
