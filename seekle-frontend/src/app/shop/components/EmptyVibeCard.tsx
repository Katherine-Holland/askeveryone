// seekle-frontend/src/app/shop/components/EmptyVibeCard.tsx
"use client";

export default function EmptyVibeCard({
  title,
  description,
  ctaLabel,
  isActive,
  onClick,
}: {
  title: string;
  description: string;
  ctaLabel: string;
  isActive?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "w-full rounded-2xl border p-3 text-left transition",
        isActive ? "border-black/20 bg-black/5" : "border-black/10 bg-white hover:bg-black/5",
      ].join(" ")}
    >
      <div className="text-sm font-semibold">{title}</div>
      <div className="mt-1 text-xs text-black/60">{description}</div>
      <div className="mt-3 inline-flex items-center rounded-xl border border-black/10 bg-white px-3 py-2 text-xs hover:bg-black/5">
        {ctaLabel} →
      </div>
    </button>
  );
}
