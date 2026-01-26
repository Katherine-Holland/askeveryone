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

  // view mode: search results vs browsing a vibe internally
  const [mode, setMode] = useState<"search" | "vibe">("search");

  // ✅ Phase 1 search wiring
  const [products, setProducts] = useState<ShopProduct[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // ✅ Phase 1 pinning (localStorage)
  const [pinsByVibe, setPinsByVibe] = useState<PinsByVibe>({});
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    setPinsByVibe(safeLoadPins());
  }, []);

  const vibesForUi: Vibe[] = useMemo(() => STARTER_VIBES, []);

  const activeVibe =
    vibesForUi.find((v) => v.id === activeVibeId) ?? vibesForUi[0];

  // ✅ counts per vibe (VibesPanel)
  const pinCountsByVibeId = useMemo(() => {
    const out: Record<string, number> = {};
    for (const v of vibesForUi) out[v.id] = (pinsByVibe[v.id] || []).length;
    return out;
  }, [pinsByVibe, vibesForUi]);

  // ✅ thumbnails per vibe (VibesPanel)
  const thumbsByVibeId = useMemo(() => {
    const out: Record<string, { id: string; imageUrl: string; title?: string }[]> =
      {};
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

  // ✅ active vibe items (browse mode)
  const activePins: ShopProduct[] = useMemo(() => {
    return pinsByVibe[activeVibeId] || [];
  }, [pinsByVibe, activeVibeId]);

  // pinned ids for the active vibe (for “Save/Remove” toggle)
  const pinnedIds = useMemo(() => {
    return new Set((pinsByVibe[activeVibeId] || []).map((p) => p.id));
  }, [pinsByVibe, activeVibeId]);

  async function runShopSearch() {
    const q = query.trim();
    if (!q || isSearching) return;

    setMode("search"); // searching always shows search grid
    setIsSearching(true);
    setSearchError(null);

    try {
      const url = new URL("/api/shop/search", window.location.origin);
      url.searchParams.set("q", q);
      if (prefs.country) url.searchParams.set("country", prefs.country);
      if (prefs.gender) url.searchParams.set("gender", prefs.gender);
      if (prefs.size) url.searchParams.set("size", prefs.size);
      url.searchParams.set("saleOnly", prefs.saleOnly ? "true" : "false");
      url.searchParams.set("pricePreset", prefs.pricePreset);
      url.searchParams.set("giftMode", prefs.giftMode ? "true" : "false");

      const r = await fetch(url.toString(), { method: "GET", cache: "no-store" });
      const data = (await r.json().catch(() => null)) as ShopSearchResponse | null;
      const apiResults = data?.results ?? [];

      setProducts(apiResults.length ? apiResults : MOCK_RESULTS);
      if (!r.ok && data?.message) setSearchError(data.message);
    } catch (e: any) {
      setProducts(MOCK_RESULTS);
      setSearchError(e?.message || "Shop search failed");
    } finally {
      setIsSearching(false);
    }
  }

  const onPin = (product: ShopProduct) => {
    setPinsByVibe((prev) => {
      const existing = prev[activeVibeId] || [];
      const already = existing.some((x) => x.id === product.id);
      if (already) return prev;

      const nextForVibe = [product, ...existing].slice(0, 200);
      const next: PinsByVibe = { ...prev, [activeVibeId]: nextForVibe };
      safeSavePins(next);
      return next;
    });

    setToast(`Saved to ${activeVibe.name}`);
    window.setTimeout(() => setToast(null), 1400);
  };

  const onRemovePin = (productId: string) => {
    setPinsByVibe((prev) => {
      const existing = prev[activeVibeId] || [];
      const nextForVibe = existing.filter((p) => p.id !== productId);
      const next: PinsByVibe = { ...prev, [activeVibeId]: nextForVibe };
      safeSavePins(next);
      return next;
    });

    setToast(`Removed from ${activeVibe.name}`);
    window.setTimeout(() => setToast(null), 1400);
  };

  const onSelectVibe = (id: string) => {
    setActiveVibeId(id);
    setMode("vibe"); // ✅ clicking a vibe opens the internal browse view
  };

  const onShareVibe = (vibeId: string) => {
    // Phase 1: keep simple. You already decided download/share formatting next.
    // eslint-disable-next-line no-alert
    alert(`Share vibe: ${vibesForUi.find((v) => v.id === vibeId)?.name || "Vibe"}`);
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
          providerLabel={isSearching ? "Searching…" : "Shop search BETA"}
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

          {/* Center: Results / Vibe Browse */}
          <div className="lg:col-span-6">
            <ShopResults
              mode={mode}
              query={query}
              prefs={prefs}
              activeVibeName={activeVibe.name}
              products={mode === "vibe" ? activePins : products}
              isSearching={isSearching}
              pinnedIds={pinnedIds}
              onPin={onPin}
              onRemovePin={onRemovePin}
            />
          </div>

          {/* Right: Vibes */}
          <div className="lg:col-span-3 space-y-3">
            <VibesPanel
              vibes={vibesForUi}
              activeVibeId={activeVibeId}
              onSelectVibe={onSelectVibe}
              onCreateVibe={() => alert("Create Vibe (coming soon)")}
              onShareVibe={onShareVibe}
              countsByVibeId={pinCountsByVibeId}
              thumbsByVibeId={thumbsByVibeId}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
