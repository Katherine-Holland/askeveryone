// seekle-frontend/src/app/shop/components/ShopPreferences.tsx
"use client";

export type GenderPref = "any" | "women" | "men" | "kids";
export type PricePreset = "any" | "budget" | "mid" | "premium";

export type ShopPrefs = {
  country: string;
  gender: GenderPref;
  size: string;
  pricePreset: PricePreset;
  saleOnly: boolean;
  giftMode: boolean;
};

export default function ShopPreferences({
  value,
  onChange,
}: {
  value: ShopPrefs;
  onChange: (next: ShopPrefs) => void;
}) {
  const set = <K extends keyof ShopPrefs>(key: K, next: ShopPrefs[K]) =>
    onChange({ ...value, [key]: next });

  const sizeDisabled = value.gender === "any" || value.giftMode;

  return (
    <aside className="rounded-2xl border border-black/10 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold">Preferences</h2>
        <span className="text-xs text-black/50">Optional</span>
      </div>

      {/* Shopper */}
      <div className="mb-4 rounded-2xl border border-black/10 p-3">
        <div className="text-xs font-medium text-black/70">Shopper</div>
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            onClick={() => set("giftMode", false)}
            className={[
              "flex-1 rounded-xl border px-3 py-2 text-sm",
              !value.giftMode ? "border-black/20 bg-black/5" : "border-black/10 bg-white hover:bg-black/5",
            ].join(" ")}
          >
            For me
          </button>
          <button
            type="button"
            onClick={() => set("giftMode", true)}
            className={[
              "flex-1 rounded-xl border px-3 py-2 text-sm",
              value.giftMode ? "border-black/20 bg-black/5" : "border-black/10 bg-white hover:bg-black/5",
            ].join(" ")}
          >
            It’s a gift
          </button>
        </div>
        {value.giftMode && (
          <p className="mt-2 text-xs text-black/60">
            Gift mode avoids assuming your personal sizes. You can still set gender/size if you want.
          </p>
        )}
      </div>

      {/* Location */}
      <div className="mb-4">
        <label className="text-xs font-medium text-black/70" htmlFor="pref-country">
          Country
        </label>
        <select
          id="pref-country"
          value={value.country}
          onChange={(e) => set("country", e.target.value)}
          className="mt-2 w-full rounded-2xl border border-black/10 bg-white px-3 py-2 text-sm outline-none focus:border-black/20"
        >
          <option value="">Select…</option>
          <option value="UK">United Kingdom</option>
          <option value="US">United States</option>
          <option value="IE">Ireland</option>
          <option value="CA">Canada</option>
          <option value="AU">Australia</option>
        </select>
        <p className="mt-2 text-xs text-black/60">
          Location improves purchasable results (currency + delivery).
        </p>
      </div>

      {/* Basics */}
      <div className="mb-4">
        <label className="text-xs font-medium text-black/70" htmlFor="pref-gender">
          Gender
        </label>
        <select
          id="pref-gender"
          value={value.gender}
          onChange={(e) => set("gender", e.target.value as GenderPref)}
          className="mt-2 w-full rounded-2xl border border-black/10 bg-white px-3 py-2 text-sm outline-none focus:border-black/20"
        >
          <option value="any">Any</option>
          <option value="women">Women</option>
          <option value="men">Men</option>
          <option value="kids">Kids</option>
        </select>
      </div>

      <div className="mb-4">
        <label className="text-xs font-medium text-black/70" htmlFor="pref-size">
          Size
        </label>
        <input
          id="pref-size"
          value={value.size}
          onChange={(e) => set("size", e.target.value)}
          placeholder={sizeDisabled ? "Disabled (choose gender or disable gift mode)" : "e.g. M, 10, 42"}
          disabled={sizeDisabled}
          className={[
            "mt-2 w-full rounded-2xl border px-3 py-2 text-sm outline-none",
            sizeDisabled
              ? "border-black/10 bg-black/5 text-black/40"
              : "border-black/10 bg-white focus:border-black/20",
          ].join(" ")}
        />
      </div>

      <div className="mb-4">
        <label className="text-xs font-medium text-black/70" htmlFor="pref-price">
          Price
        </label>
        <select
          id="pref-price"
          value={value.pricePreset}
          onChange={(e) => set("pricePreset", e.target.value as PricePreset)}
          className="mt-2 w-full rounded-2xl border border-black/10 bg-white px-3 py-2 text-sm outline-none focus:border-black/20"
        >
          <option value="any">Any</option>
          <option value="budget">Budget</option>
          <option value="mid">Mid</option>
          <option value="premium">Premium</option>
        </select>
      </div>

      <div className="flex items-center justify-between rounded-2xl border border-black/10 p-3">
        <div>
          <div className="text-sm font-medium">Sale only</div>
          <div className="text-xs text-black/60">Prefer discounted items</div>
        </div>
        <button
          type="button"
          onClick={() => set("saleOnly", !value.saleOnly)}
          className={[
            "h-8 w-14 rounded-full border transition",
            value.saleOnly ? "border-black/20 bg-black/20" : "border-black/10 bg-black/5",
          ].join(" ")}
          aria-pressed={value.saleOnly}
          aria-label="Toggle sale only"
        >
          <span
            className={[
              "block h-7 w-7 rounded-full bg-white shadow-sm transition",
              value.saleOnly ? "translate-x-6" : "translate-x-0",
            ].join(" ")}
          />
        </button>
      </div>
    </aside>
  );
}
