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

function slugify(name: string) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
    .slice(0, 64);
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function loadImageSafe(src: string, timeoutMs = 4500): Promise<HTMLImageElement | null> {
  try {
    const img = new Image();
    img.crossOrigin = "anonymous";

    const done = new Promise<HTMLImageElement>((resolve, reject) => {
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("image load failed"));
    });

    img.src = src;

    const timeout = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error("image timeout")), timeoutMs)
    );

    return await Promise.race([done, timeout]);
  } catch {
    return null;
  }
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

  // ✅ Search wiring
  const [products, setProducts] = useState<ShopProduct[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // ✅ Pinning (localStorage)
  const [pinsByVibe, setPinsByVibe] = useState<PinsByVibe>({});
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    setPinsByVibe(safeLoadPins());
  }, []);

  const vibesForUi: Vibe[] = useMemo(() => STARTER_VIBES, []);

  const activeVibe =
    vibesForUi.find((v) => v.id === activeVibeId) ?? vibesForUi[0];

  // ✅ pin counts per vibe
  const pinCountsByVibeId = useMemo(() => {
    const out: Record<string, number> = {};
    for (const v of vibesForUi) out[v.id] = (pinsByVibe[v.id] || []).length;
    return out;
  }, [pinsByVibe, vibesForUi]);

  // ✅ thumbs per vibe
  const thumbsByVibeId = useMemo(() => {
    const out: Record<string, { id: string; imageUrl: string; title?: string }[]> = {};
    for (const v of vibesForUi) {
      const pins = pinsByVibe[v.id] || [];
      out[v.id] = pins.map((p) => ({ id: p.id, imageUrl: p.imageUrl, title: p.title }));
    }
    return out;
  }, [pinsByVibe, vibesForUi]);

  // ✅ active pins
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
      const nextForVibe = already ? existing : [product, ...existing].slice(0, 200);
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

  const onClearVibe = () => {
    setPinsByVibe((prev) => {
      const next: PinsByVibe = { ...prev, [activeVibeId]: [] };
      safeSavePins(next);
      return next;
    });

    setToast(`Cleared ${activeVibe.name}`);
    window.setTimeout(() => setToast(null), 1400);
  };

  const onShareVibe = async (vibeId: string) => {
    const vibe = vibesForUi.find((v) => v.id === vibeId) || activeVibe;
    const pins = (pinsByVibe[vibeId] || []).slice(0, 6);

    if (!pins.length) {
      setToast("No saved items to share yet");
      window.setTimeout(() => setToast(null), 1400);
      return;
    }

    setToast("Preparing vibe download…");

    const W = 1080;
    const H = 1920;

    const pad = 72;
    const gap = 22;
    const headerH = 190;

    const cols = 2;
    const rows = 3;

    const gridW = W - pad * 2;
    const gridH = H - pad * 2 - headerH;

    const tileW = Math.floor((gridW - gap * (cols - 1)) / cols);
    const tileH = Math.floor((gridH - gap * (rows - 1)) / rows);

    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const drawBase = () => {
      ctx.fillStyle = "#f7f7f7";
      ctx.fillRect(0, 0, W, H);

      ctx.fillStyle = "#111111";
      ctx.font = "700 56px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial";
      ctx.fillText("seekle", pad, 95);

      ctx.fillStyle = "rgba(0,0,0,0.7)";
      ctx.font = "600 44px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial";
      ctx.fillText(vibe.name, pad, 155);

      ctx.fillStyle = "rgba(0,0,0,0.45)";
      ctx.font = "500 28px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial";
      ctx.fillText("Vibe board", pad, 190);

      ctx.fillStyle = "rgba(0,0,0,0.35)";
      ctx.font = "700 34px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial";
      ctx.textAlign = "right";
      ctx.fillText("seekle.io", W - pad, H - 48);
      ctx.textAlign = "left";
    };

    const drawPlaceholderTile = (x: number, y: number, w: number, h: number) => {
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(x, y, w, h);
      ctx.strokeStyle = "rgba(0,0,0,0.08)";
      ctx.lineWidth = 2;
      ctx.strokeRect(x + 1, y + 1, w - 2, h - 2);

      ctx.fillStyle = "rgba(0,0,0,0.35)";
      ctx.font = "600 26px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial";
      ctx.fillText("seekle", x + 22, y + 44);
    };

    const drawImageCover = (img: HTMLImageElement, x: number, y: number, w: number, h: number) => {
      const ir = img.width / img.height;
      const tr = w / h;

      let sx = 0,
        sy = 0,
        sw = img.width,
        sh = img.height;

      if (ir > tr) {
        sh = img.height;
        sw = Math.floor(sh * tr);
        sx = Math.floor((img.width - sw) / 2);
      } else {
        sw = img.width;
        sh = Math.floor(sw / tr);
        sy = Math.floor((img.height - sh) / 2);
      }

      ctx.save();
      const r = 28;
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + w, y, x + w, y + h, r);
      ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r);
      ctx.arcTo(x, y, x + w, y, r);
      ctx.closePath();
      ctx.clip();

      ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h);

      ctx.fillStyle = "rgba(255,255,255,0.08)";
      ctx.fillRect(x, y, w, h);

      ctx.restore();

      ctx.strokeStyle = "rgba(0,0,0,0.07)";
      ctx.lineWidth = 2;
      ctx.strokeRect(x + 1, y + 1, w - 2, h - 2);
    };

    drawBase();

    const imgs = await Promise.all(pins.map((p) => loadImageSafe(p.imageUrl)));

    let idx = 0;
    const startY = pad + headerH;

    for (let rr = 0; rr < rows; rr++) {
      for (let cc = 0; cc < cols; cc++) {
        const x = pad + cc * (tileW + gap);
        const y = startY + rr * (tileH + gap);

        const img = imgs[idx] || null;
        if (img) drawImageCover(img, x, y, tileW, tileH);
        else drawPlaceholderTile(x, y, tileW, tileH);

        idx++;
      }
    }

    try {
      const blob: Blob | null = await new Promise((resolve) =>
        canvas.toBlob((b) => resolve(b), "image/jpeg", 0.92)
      );

      if (!blob) throw new Error("toBlob failed");

      downloadBlob(blob, `seekle-vibe-${slugify(vibe.name)}.jpg`);
      setToast("Vibe downloaded");
      window.setTimeout(() => setToast(null), 1400);
    } catch {
      setToast("Couldn’t include some images. Try again later.");
      window.setTimeout(() => setToast(null), 1400);
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

            {/* ✅ Saved lookbook panel */}
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
                  Nothing saved yet. Tap <span className="font-medium">♡ Save</span> to build your vibe.
                </div>
              ) : (
                <>
                  {/* Premium mini lookbook grid */}
                  <div className="grid grid-cols-2 gap-3">
                    {activePins.slice(0, 8).map((p) => (
                      <article
                        key={p.id}
                        className="group overflow-hidden rounded-2xl border border-black/10 bg-white transition-all duration-200 hover:-translate-y-[1px] hover:shadow-md"
                      >
                        <a
                          href={p.href || "#"}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="block"
                          title="Open in a new tab"
                        >
                          <div className="relative aspect-[3/4] w-full bg-black/[0.04]">
                            <img
                              src={p.imageUrl || "/window.svg"}
                              alt={p.title}
                              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                              loading="lazy"
                            />
                            <div className="absolute bottom-2 right-2 rounded-full border border-white/30 bg-black/30 px-2 py-0.5 text-[11px] text-white backdrop-blur">
                              seekle
                            </div>
                          </div>
                        </a>

                        <div className="p-3">
                          <div className="line-clamp-1 text-xs font-semibold">
                            {p.title}
                          </div>
                          <div className="mt-0.5 line-clamp-1 text-[11px] text-black/60">
                            {p.merchant}
                          </div>

                          <div className="mt-3 flex items-center gap-2">
                            <a
                              href={p.href || "#"}
                              target="_blank"
                              rel="noreferrer noopener"
                              className="flex-1 rounded-xl border border-black/10 bg-white px-2 py-2 text-center text-xs hover:bg-black/5"
                            >
                              Open
                            </a>
                            <button
                              type="button"
                              onClick={() => onRemovePin(p.id)}
                              className="rounded-xl border border-black/10 bg-black px-2 py-2 text-xs text-white hover:opacity-90"
                              title="Remove"
                            >
                              Remove
                            </button>
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>

                  {activePins.length > 8 ? (
                    <div className="mt-3 text-xs text-black/50">
                      Showing 8 of {activePins.length}.
                    </div>
                  ) : null}
                </>
              )}
            </aside>
          </div>
        </div>
      </div>
    </div>
  );
}
