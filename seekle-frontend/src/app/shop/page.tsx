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

  // ✅ Phase 1 search wiring
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
    return STARTER_VIBES;
  }, []);

  const activeVibe =
    vibesForUi.find((v) => v.id === activeVibeId) ?? vibesForUi[0];

  // ✅ derive pin counts per vibe (for UI)
  const pinCountsByVibeId = useMemo(() => {
    const out: Record<string, number> = {};
    for (const v of vibesForUi) out[v.id] = (pinsByVibe[v.id] || []).length;
    return out;
  }, [pinsByVibe, vibesForUi]);

  // ✅ thumbnails per vibe (for VibesPanel)
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

  // ✅ active vibe saved items
  const activePins: ShopProduct[] = useMemo(() => {
    return pinsByVibe[activeVibeId] || [];
  }, [pinsByVibe, activeVibeId]);

  async function runShopSearch() {
    const q = query.trim();
    if (!q || isSearching) return;

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

      const r = await fetch(url.toString(), {
        method: "GET",
        cache: "no-store",
      });

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

      const nextForVibe = already
        ? existing
        : [product, ...existing].slice(0, 200);

      const next: PinsByVibe = { ...prev, [activeVibeId]: nextForVibe };
      safeSavePins(next);
      return next;
    });

    setToast(`Saved to ${activeVibe.name}`);
    window.setTimeout(() => setToast(null), 1600);
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
    window.setTimeout(() => setToast(null), 1600);
  };

  const onClearVibe = () => {
    setPinsByVibe((prev) => {
      const next: PinsByVibe = { ...prev, [activeVibeId]: [] };
      safeSavePins(next);
      return next;
    });

    setToast(`Cleared ${activeVibe.name}`);
    window.setTimeout(() => setToast(null), 1600);
  };

  // ✅ NEW: Share Vibe (branded Seekle link)
  const onShareVibe = (vibeId: string) => {
    const vibe = vibesForUi.find((v) => v.id === vibeId);
    const name = vibe?.name || "Vibe";

    const shareUrl = `${window.location.origin}/shop?vibe=${encodeURIComponent(
      vibeId
    )}`;
    const text = `Seekle Vibe: ${name}`;

    const doCopy = async () => {
      try {
        await navigator.clipboard.writeText(shareUrl);
        setToast("Link copied — share it on TikTok ✨");
        window.setTimeout(() => setToast(null), 1600);
      } catch {
        // Fallback if clipboard blocked
        // eslint-disable-next-line no-alert
        window.prompt("Copy this link:", shareUrl);
      }
    };

    if (navigator.share) {
      void navigator
        .share({ title: `Seekle Vibe — ${name}`, text, url: shareUrl })
        .catch(() => void doCopy());
    } else {
      void doCopy();
    }
  };

  return (
    <div className="min-h-[70vh] px-4 py-6">
      {/* Toast */}
      {toast ? (
        <div className="fixed left-1/2 top-6 z-50 -translate-x-1/2">
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

          {/* Right: Vibes + Saved */}
          <div className="lg:col-span-3 space-y-3">
            <VibesPanel
              vibes={vibesForUi}
              activeVibeId={activeVibeId}
              onSelectVibe={setActiveVibeId}
              onCreateVibe={() => alert("Create Vibe (coming soon)")}
              onShareVibe={onShareVibe}
              countsByVibeId={pinCountsByVibeId}
              thumbsByVibeId={thumbsByVibeId}
            />

            {/* ✅ Saved items for the active vibe */}
            <aside className="rounded-2xl border border-black/10 bg-white p-4">
              <div className="mb-3 flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold">Saved</h3>
                  <p className="text-xs text-black/60">
                    In <span className="font-medium">{activeVibe.name}</span>
                  </p>
                </div>

                <button
                  type="button"
                  onClick={onClearVibe}
                  disabled={activePins.length === 0}
                  className="rounded-xl border border-black/10 bg-white px-3 py-2 text-sm hover:bg-black/5 disabled:opacity-50"
                  title="Clear saved items in this vibe"
                >
                  Clear
                </button>
              </div>

              {activePins.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-black/15 bg-black/[0.02] p-4 text-sm text-black/60">
                  Nothing saved yet. Tap{" "}
                  <span className="font-medium">Save</span> on a result to add it
                  here.
                </div>
              ) : (
                <div className="space-y-2">
                  {activePins.slice(0, 8).map((p) => (
                    <div
                      key={p.id}
                      className="flex items-center gap-3 rounded-2xl border border-black/10 bg-white p-2"
                    >
                      <div className="h-10 w-10 overflow-hidden rounded-xl border border-black/10 bg-black/5">
                        <img
                          src={p.imageUrl}
                          alt=""
                          className="h-full w-full object-contain p-1"
                          loading="lazy"
                        />
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium">
                          {p.title}
                        </div>
                        <div className="mt-0.5 text-xs text-black/60">
                          {p.price} · {p.merchant}
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => onRemovePin(p.id)}
                        className="rounded-xl border border-black/10 bg-white px-2 py-1 text-xs hover:bg-black/5"
                        title="Remove"
                      >
                        Remove
                      </button>
                    </div>
                  ))}

                  {activePins.length > 8 ? (
                    <div className="text-xs text-black/50">
                      Showing 8 of {activePins.length}. (“View all” page in BETA.)
                    </div>
                  ) : null}
                </div>
              )}
            </aside>
          </div>
        </div>
      </div>
    </div>
  );
}
