// seekle-frontend/src/app/shop/components/ShopHeader.tsx
"use client";

export default function ShopHeader({
  query,
  setQuery,
  providerLabel,
  onSearch,
  isSearching,
}: {
  query: string;
  setQuery: (v: string) => void;
  providerLabel: string;
  onSearch: () => void;
  isSearching: boolean;
}) {
  return (
    <div className="rounded-2xl border border-black/10 bg-white p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex-1">
          <label className="text-sm font-medium" htmlFor="shop-search">
            What are you shopping for?
          </label>

          <div className="mt-2 flex items-center gap-2">
            <input
              id="shop-search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  onSearch();
                }
              }}
              disabled={isSearching}
              placeholder='Try: "red coat in the sale"'
              className="w-full rounded-2xl border border-black/10 bg-white px-4 py-3 text-sm outline-none focus:border-black/20 disabled:bg-black/5 disabled:text-black/50"
            />
          </div>

          <p className="mt-2 text-xs text-black/60">
            Results will be tailored using your Preferences + Vibe.
          </p>
        </div>

        <div className="flex items-center justify-between gap-3 sm:flex-col sm:items-end sm:justify-center">
          <div className="rounded-2xl border border-black/10 bg-black/5 px-3 py-2 text-xs">
            <span className="inline-flex items-center gap-2">
              {isSearching ? (
                <span
                  className="inline-block h-3 w-3 animate-spin rounded-full border border-black/30 border-t-transparent"
                  aria-label="Searching"
                />
              ) : null}
              Provider: <span className="font-medium">{providerLabel}</span>
            </span>
          </div>
          <div className="text-xs text-black/50">
            Purchasable results only (soon)
          </div>
        </div>
      </div>
    </div>
  );
}
