// seekle-frontend/src/app/shop/loading.tsx
export default function Loading() {
  return (
    <div className="min-h-[70vh] px-4 py-6">
      <div className="mx-auto w-full max-w-6xl">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div className="h-10 w-[420px] max-w-full animate-pulse rounded-2xl bg-black/10" />
          <div className="h-10 w-28 animate-pulse rounded-2xl bg-black/10" />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="lg:col-span-3">
            <div className="h-[520px] animate-pulse rounded-2xl bg-black/10" />
          </div>
          <div className="lg:col-span-6">
            <div className="h-[520px] animate-pulse rounded-2xl bg-black/10" />
          </div>
          <div className="lg:col-span-3">
            <div className="h-[520px] animate-pulse rounded-2xl bg-black/10" />
          </div>
        </div>
      </div>
    </div>
  );
}
