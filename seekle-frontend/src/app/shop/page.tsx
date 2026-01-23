// seekle-frontend/src/app/shop/page.tsx
"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import ShopHeader from "./components/ShopHeader";
import ShopPreferences, { ShopPrefs } from "./components/ShopPreferences";
import ShopResults, { ShopProduct } from "./components/ShopResults";
import VibesPanel, { Vibe } from "./components/VibesPanel";

const STARTER_VIBES: Vibe[] = [
  {
    id: "starter-everyday",
    name: "Everyday Vibe",
    description: "Start shopping to add your favourite everyday finds here.",
    isStarter: true,
  },
  {
    id: "starter-occasion",
    name: "Occasion Vibe",
    description: "Nights out, events, and special plans — save the best picks.",
    isStarter: true,
  },
  {
    id: "starter-gifts",
    name: "Gift Vibe",
    description: "Ideas for someone else — save gift options as you browse.",
    isStarter: true,
  },
];

const MOCK_RESULTS: ShopProduct[] = [
  {
    id: "m1",
    title: "Red Wool Blend Coat",
    price: "£89.00",
    merchant: "Example Store",
    imageUrl: "/window.svg",
    href: "#",
    badges: ["Sale"],
  },
  {
    id: "m2",
    title: "Cherry Red Trench Coat",
    price: "£120.00",
    merchant: "Example Store",
    imageUrl: "/globe.svg",
    href: "#",
    badges: ["Sale"],
  },
  {
    id: "m3",
    title: "Deep Red Puffer Jacket",
    price: "£65.00",
    merchant: "Example Store",
    imageUrl: "/file.svg",
    href: "#",
    badges: ["Sale"],
  },
];

export default function ShopPage() {
  const [query, setQuery] = useState("");
  const [prefs, setPrefs] = useState<ShopPrefs>({
    country: "",
    gender: "any",
    size: "",
    pricePreset: "any",
    saleOnly: true,
    giftMode: false,
  });

  const [activeVibeId, setActiveVibeId] = useState<string>(STARTER_VIBES[0].id);

  // Phase 1 UI-only: show “results” once user types anything.
  const results = useMemo(() => {
    if (!query.trim()) return [];
    return MOCK_RESULTS;
  }, [query]);

  const vibesForUi: Vibe[] = useMemo(() => {
    // Later: merge real vibes from DB with starters.
    return STARTER_VIBES;
  }, []);

  const activeVibe = vibesForUi.find((v) => v.id === activeVibeId) ?? vibesForUi[0];

  const onPin = (product: ShopProduct) => {
    // Phase 1: no DB yet. Just a friendly toast-ish state.
    // You can swap this for a real pin action once Neon is wired.
    // eslint-disable-next-line no-alert
    alert(`Saved "${product.title}" to ${activeVibe.name}`);
  };

  return (
    <div className="min-h-[70vh] px-4 py-6">
      <div className="mx-auto w-full max-w-6xl">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold tracking-tight">Seekle Shop</h1>
            <span className="rounded-full border border-black/10 bg-black/5 px-2 py-0.5 text-xs">
              Phase 1
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/"
              className="rounded-xl border border-black/10 bg-white px-3 py-2 text-sm hover:bg-black/5"
            >
              ← Ask Everyone
            </Link>
          </div>
        </div>

        <ShopHeader query={query} setQuery={setQuery} providerLabel="Shopify (soon)" />

        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-12">
          {/* Left: Preferences */}
          <div className="lg:col-span-3">
            <ShopPreferences value={prefs} onChange={setPrefs} />
          </div>

          {/* Center: Results */}
          <div className="lg:col-span-6">
            <ShopResults
              query={query}
              prefs={prefs}
              activeVibeName={activeVibe.name}
              products={results}
              onPin={onPin}
            />
          </div>

          {/* Right: Vibes */}
          <div className="lg:col-span-3">
            <VibesPanel
              vibes={vibesForUi}
              activeVibeId={activeVibeId}
              onSelectVibe={setActiveVibeId}
              onCreateVibe={() => alert("Create Vibe (coming soon)")}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
