// seekle-frontend/src/app/shop/page.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
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

type ShopSearchResponse = {
  ok?: boolean;
  message?: string;
  query?: string;
  results?: ShopProduct[];
};

// ✅ Phase 1 pinning storage key
const LS_PINS_V1 = "seekle_shop_pins_v1";

// Map of vibeId -> pinned products
type PinsByVibe = Record<string, ShopProduct[]>;

function safeLoadPins(): PinsByVibe {
  try {
    if (typeof window === "undefined") return {};
    const raw = localStorage.getItem(LS_PINS_V1);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return {};
    return parsed as PinsByVibe;
  } catch {
    return {};
  }
}

function safeSavePins(next: PinsByVibe) {
  try {
    if (typeof window === "undefined") return;
    localStorage.setItem(LS_PINS_V1, JSON.stringify(next));
  } catch {}
}

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

  // ✅ Phase 1 search wiring (still mock backend, but real plumbing)
  const [products, setProducts] = useState<ShopProduct[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // ✅ Phase 1 pinning (localStorage)
  const [pinsByVibe, setPinsByVibe] = useState<PinsByVibe>({});
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    // hydrate pins on first client render
    setPinsByVibe(safeLoadPins());
  }, []);

  const vibesForUi: Vibe[] = useMemo(() => {
    // Later: merge real vibes from DB with starters.
    return STARTER_VIBES;
  }, []);

  const activeVibe =
    vibesForUi.find((v) => v.id === activeVibeId) ?? vibesForUi[0];

  // ✅ derive pin counts per vibe (for UI + future VibesPanel integration)
  const pinCountsByVibeId = useMemo(() => {
    const out: Record<string, number> = {};
    for (const v of vibesForUi) out[v.id] = (pinsByVibe[v.id] || []).length;
    return out;
  }, [pinsByVibe, vibesForUi]);

  const thumbsByVibeId = useMemo(() => {
  const out: Record<string, { id: string; imageUrl: string; title?: string }[]> = {};

  for (const v of vibesForUi) {
    const pins = pinsByVibe[v.id] || [];
    out[v.id] = pins.map((p) => ({
      id: p.id,
      imageUrl: p.imageUrl,
      title: p.title,
    }));
  }

  return out;
}, [pinsByVibe, vibesForUi]);


  async function runShopSearch() {
    const q = query.trim();
    if (!q || isSearching) return;

    setIsSearching(true);
    setSearchError(null);

    try {
      // Keep it simple: send q + a few prefs.
      // Later we can send full prefs as JSON and/or include vibe context.
      const url = new URL("/api/shop/search", window.location.origin);
      url.searchParams.set("q", q);
      if (prefs.country) url.searchParams.set("country", prefs.country);
      if (prefs.gender) url.searchParams.set("gender", prefs.gender);
      if (prefs.size) url.searchParams.set("size", prefs.size);
      url.searchParams.set("saleOnly", prefs.saleOnly ? "true" : "false");
      url.searchParams.set("pricePreset", prefs.pricePreset);
      url.searchParams.set("giftMode", prefs.giftMode ? "true" : "false");

      const r = await fetch(url.toString(), {
        method: "GET",
        cache: "no-store",
      });

      // If the stub returns 501, we still want the UI to show something useful.
      const data = (await r.json().catch(() => null)) as ShopSearchResponse | null;

      const apiResults = data?.results ?? [];

      // Fallback: if API returns no results (or stub), show mock results to keep UX alive.
      setProducts(apiResults.length ? apiResults : MOCK_RESULTS);

      // If it’s a stub response, show a subtle message (optional).
      if (!r.ok && data?.message) {
        setSearchError(data.message);
      }
    } catch (e: any) {
      setProducts(MOCK_RESULTS);
      setSearchError(e?.message || "Shop search failed");
    } finally {
      setIsSearching(false);
    }
  }

  const onPin = (product: ShopProduct) => {
    // ✅ Phase 1: pin to localStorage, de-dupe by product.id per vibe
    setPinsByVibe((prev) => {
      const existing = prev[activeVibeId] || [];
      const already = existing.some((x) => x.id === product.id);

      const nextForVibe = already ? existing : [product, ...existing].slice(0, 200);
      const next: PinsByVibe = { ...prev, [activeVibeId]: nextForVibe };

      safeSavePins(next);
      return next;
    });

    // ✅ toast
    setToast(`Saved to ${activeVibe.name}`);
    window.clearTimeout((onPin as any)._t);
    (onPin as any)._t = window.setTimeout(() => setToast(null), 1600);
  };

  return (
    <div className="min-h-[70vh] px-4 py-6">
      {/* Toast */}
      {toast ? (
        <div className="fixed top-6 left-1/2 z-50 -translate-x-1/2">
          <div className="rounded-full border border-black/10 bg-white px-4 py-2 text-sm shadow-sm">
            {toast}
          </div>
        </div>
      ) : null}

      <div className="mx-auto w-full max-w-6xl">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold tracking-tight">Seekle Shop</h1>
            <span className="rounded-full border border-black/10 bg-black/5 px-2 py-0.5 text-xs">
              BETA
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/"
              className="rounded-xl border border-black/10 bg-white px-3 py-2 text-sm hover:bg-black/5"
            >
              ← Home
            </Link>
          </div>
        </div>

        <ShopHeader
          query={query}
          setQuery={setQuery}
          providerLabel={isSearching ? "Searching…" : "Shop search (stub)"}
          onSearch={runShopSearch}
          isSearching={isSearching}
        />

        {searchError ? (
          <div className="mt-4 rounded-2xl border border-black/10 bg-black/[0.02] px-4 py-3 text-sm text-black/70">
            {searchError}
          </div>
        ) : null}

        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-12">
          {/* Left: Preferences */}
          <div className="lg:col-span-3">
            <ShopPreferences value={prefs} onChange={setPrefs} />
            <div className="mt-3 text-xs text-black/50">
              Tip: press <span className="font-medium">Enter</span> to search.
            </div>
          </div>

          {/* Center: Results */}
          <div className="lg:col-span-6">
            <ShopResults
              query={query}
              prefs={prefs}
              activeVibeName={activeVibe.name}
              products={products}
              onPin={onPin}
              isSearching={isSearching}
            />
          </div>

          {/* Right: Vibes */}
          <div className="lg:col-span-3">
            {/* Phase 1: we’re not rendering counts inside VibesPanel yet.
                But pinCountsByVibeId is computed and ready for the next step (VibesPanel). */}
            <div className="mb-2 text-xs text-black/50">
              Saved:{" "}
              <span className="font-medium">
                {pinCountsByVibeId[activeVibeId] ?? 0}
              </span>
            </div>

            <VibesPanel
              vibes={vibesForUi}
              activeVibeId={activeVibeId}
              onSelectVibe={setActiveVibeId}
              onCreateVibe={() => alert("Create Vibe (coming soon)")}
              countsByVibeId={pinCountsByVibeId}
              thumbsByVibeId={thumbsByVibeId}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
