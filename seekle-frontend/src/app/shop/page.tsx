// seekle-frontend/src/app/shop/page.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import ShopHeader from "./components/ShopHeader";
import ShopPreferences, { ShopPrefs } from "./components/ShopPreferences";
import ShopResults, { ShopProduct } from "./components/ShopResults";
import VibesPanel, { Vibe } from "./components/VibesPanel";

const STARTER_VIBES: Vibe[] = [
  { id: "starter-everyday", name: "Everyday Vibe", description: "Start shopping to add your favourite everyday finds here.", isStarter: true },
  { id: "starter-occasion", name: "Occasion Vibe", description: "Nights out, events, and special plans — save the best picks.", isStarter: true },
  { id: "starter-gifts", name: "Gift Vibe", description: "Ideas for someone else — save gift options as you browse.", isStarter: true },
];

const MOCK_RESULTS: ShopProduct[] = [
  { id: "m1", title: "Red Wool Blend Coat", price: "£89.00", merchant: "Example Store", imageUrl: "/window.svg", href: "#", badges: ["Sale"] },
  { id: "m2", title: "Cherry Red Trench Coat", price: "£120.00", merchant: "Example Store", imageUrl: "/globe.svg", href: "#", badges: ["Sale"] },
  { id: "m3", title: "Deep Red Puffer Jacket", price: "£65.00", merchant: "Example Store", imageUrl: "/file.svg", href: "#", badges: ["Sale"] },
];

type ShopSearchResponse = {
  ok?: boolean;
  message?: string;
  query?: string;
  results?: ShopProduct[];
};

const LS_PINS_V1 = "seekle_shop_pins_v1";
type PinsByVibe = Record<string, ShopProduct[]>;

function safeLoadPins(): PinsByVibe {
  try {
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
    localStorage.setItem(LS_PINS_V1, JSON.stringify(next));
  } catch {}
}

function shuffleArray<T>(arr: T[]) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

async function loadImageViaProxy(src: string): Promise<HTMLImageElement | null> {
  try {
    const proxyUrl = `/api/image-proxy?src=${encodeURIComponent(src)}`;
    const r = await fetch(proxyUrl, { cache: "no-store" });
    if (!r.ok) return null;

    const blob = await r.blob();
    const objUrl = URL.createObjectURL(blob);

    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = objUrl;

    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error("img load failed"));
    });

    URL.revokeObjectURL(objUrl);
    return img;
  } catch {
    return null;
  }
}

async function downloadVibeAsJpg(opts: {
  vibeName: string;
  items: ShopProduct[];
}) {
  const { vibeName, items } = opts;

  // 6-up grid JPG (TikTok-friendly)
  const W = 1080;
  const H = 1920;

  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  // Background
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, W, H);

  // Header
  ctx.fillStyle = "rgba(0,0,0,0.9)";
  ctx.font = "bold 54px system-ui, -apple-system, Segoe UI, Roboto";
  ctx.fillText("Seekle", 72, 120);

  ctx.fillStyle = "rgba(0,0,0,0.55)";
  ctx.font = "28px system-ui, -apple-system, Segoe UI, Roboto";
  ctx.fillText(vibeName, 72, 168);

  // Grid layout: 2 cols x 3 rows
  const gridTop = 240;
  const pad = 36;
  const cols = 2;
  const rows = 3;
  const cellW = Math.floor((W - pad * 3) / 2);
  const cellH = Math.floor((H - gridTop - pad * (rows + 1)) / rows);

  const six = items.slice(0, 6);

  // Load images via proxy (best-effort)
  const imgs = await Promise.all(
    six.map(async (p) => {
      const img = await loadImageViaProxy(p.imageUrl);
      return img;
    })
  );

  for (let i = 0; i < six.length; i++) {
    const r = Math.floor(i / cols);
    const c = i % cols;

    const x = pad + c * (cellW + pad);
    const y = gridTop + pad + r * (cellH + pad);

    // Card bg
    ctx.fillStyle = "rgba(0,0,0,0.03)";
    roundRect(ctx, x, y, cellW, cellH, 28);
    ctx.fill();

    // Image
    const img = imgs[i];
    if (img) {
      // cover fit
      const iw = img.width;
      const ih = img.height;
      const scale = Math.max(cellW / iw, cellH / ih);
      const dw = iw * scale;
      const dh = ih * scale;
      const dx = x + (cellW - dw) / 2;
      const dy = y + (cellH - dh) / 2;

      ctx.save();
      roundRect(ctx, x, y, cellW, cellH, 28);
      ctx.clip();
      ctx.drawImage(img, dx, dy, dw, dh);
      ctx.restore();
    }

    // Title overlay
    ctx.fillStyle = "rgba(0,0,0,0.55)";
    ctx.font = "22px system-ui, -apple-system, Segoe UI, Roboto";
    const t = six[i].title || "";
    drawEllipsizedText(ctx, t, x + 18, y + cellH - 22, cellW - 36);
  }

  // Watermark bottom-right
  ctx.fillStyle = "rgba(0,0,0,0.35)";
  ctx.font = "bold 34px system-ui, -apple-system, Segoe UI, Roboto";
  const wm = "seekle.io";
  const mw = ctx.measureText(wm).width;
  ctx.fillText(wm, W - mw - 54, H - 72);

  // Export jpg
  const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
  const a = document.createElement("a");
  a.href = dataUrl;
  a.download = `seekle-${slugify(vibeName)}.jpg`;
  a.click();
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  const rr = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}

function drawEllipsizedText(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, maxW: number) {
  const ell = "…";
  if (ctx.measureText(text).width <= maxW) {
    ctx.fillText(text, x, y);
    return;
  }
  let t = text;
  while (t.length > 0 && ctx.measureText(t + ell).width > maxW) {
    t = t.slice(0, -1);
  }
  ctx.fillText(t + ell, x, y);
}

function slugify(s: string) {
  return (s || "vibe")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
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
  const [mode, setMode] = useState<"search" | "vibe">("search");

  const [products, setProducts] = useState<ShopProduct[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [pinsByVibe, setPinsByVibe] = useState<PinsByVibe>({});
  const [toast, setToast] = useState<string | null>(null);

  // Local “view order” for vibe browse
  const [vibeViewItems, setVibeViewItems] = useState<ShopProduct[]>([]);

  useEffect(() => {
    setPinsByVibe(safeLoadPins());
  }, []);

  const vibesForUi: Vibe[] = useMemo(() => STARTER_VIBES, []);
  const activeVibe = vibesForUi.find((v) => v.id === activeVibeId) ?? vibesForUi[0];

  const activePins: ShopProduct[] = useMemo(() => pinsByVibe[activeVibeId] || [], [pinsByVibe, activeVibeId]);

  // When switching vibes or pins change, refresh vibe view
  useEffect(() => {
    setVibeViewItems(activePins);
  }, [activeVibeId, activePins.length]);

  const pinCountsByVibeId = useMemo(() => {
    const out: Record<string, number> = {};
    for (const v of vibesForUi) out[v.id] = (pinsByVibe[v.id] || []).length;
    return out;
  }, [pinsByVibe, vibesForUi]);

  const thumbsByVibeId = useMemo(() => {
    const out: Record<string, { id: string; imageUrl: string; title?: string }[]> = {};
    for (const v of vibesForUi) {
      const pins = pinsByVibe[v.id] || [];
      out[v.id] = pins.map((p) => ({ id: p.id, imageUrl: p.imageUrl, title: p.title }));
    }
    return out;
  }, [pinsByVibe, vibesForUi]);

  const pinnedIds = useMemo(() => new Set((pinsByVibe[activeVibeId] || []).map((p) => p.id)), [pinsByVibe, activeVibeId]);

  async function runShopSearch() {
    const q = query.trim();
    if (!q || isSearching) return;

    setMode("search");
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

      // ✅ fetch more than 6 so we can paginate client-side
      url.searchParams.set("limit", "10");

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
      if (existing.some((x) => x.id === product.id)) return prev;

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
    setMode("vibe");
    setVibeViewItems(pinsByVibe[id] || []);
  };

  const onShuffleVibe = () => {
    setVibeViewItems((prev) => shuffleArray(prev));
    setToast("Shuffled vibe");
    window.setTimeout(() => setToast(null), 900);
  };

  const onShareVibe = async (vibeId: string) => {
    const vibe = vibesForUi.find((v) => v.id === vibeId) ?? activeVibe;
    const pins = pinsByVibe[vibeId] || [];

    if (!pins.length) {
      alert("Nothing saved in this vibe yet.");
      return;
    }

    // downloads a TikTok-friendly 1080x1920 JPG
    await downloadVibeAsJpg({ vibeName: vibe.name, items: pins });
  };

  const displayProducts = mode === "vibe" ? vibeViewItems : products;

  return (
    <div className="min-h-[70vh] px-4 py-6">
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
          <div className="lg:col-span-3">
            <ShopPreferences value={prefs} onChange={setPrefs} />
            <div className="mt-3 text-xs text-black/50">
              Tip: press <span className="font-medium">Enter</span> to search.
            </div>
          </div>

          <div className="lg:col-span-6">
            <ShopResults
              mode={mode}
              query={query}
              prefs={prefs}
              activeVibeName={activeVibe.name}
              products={displayProducts}
              isSearching={isSearching}
              pinnedIds={pinnedIds}
              onPin={onPin}
              onRemovePin={onRemovePin}
              onShuffleVibe={onShuffleVibe}
            />
          </div>

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
