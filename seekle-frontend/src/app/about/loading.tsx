// src/app/about/loading.tsx
export default function LoadingAbout() {
  return (
    <main className="min-h-screen bg-seekle-cream text-seekle-text">
      <div className="mx-auto max-w-4xl px-6 py-14">
        <div className="animate-pulse">
          {/* Header */}
          <div className="text-center">
            <div className="mx-auto h-3 w-28 rounded-full bg-zinc-200" />
            <div className="mx-auto mt-4 h-10 w-64 rounded-xl bg-zinc-200" />
            <div className="mx-auto mt-4 h-4 w-[85%] max-w-2xl rounded-full bg-zinc-200" />
            <div className="mx-auto mt-3 h-4 w-[72%] max-w-xl rounded-full bg-zinc-200" />
          </div>

          {/* Cards */}
          <div className="mt-12 grid gap-6">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="rounded-2xl border border-seekle-border bg-white p-6"
              >
                <div className="h-5 w-52 rounded-lg bg-zinc-200" />
                <div className="mt-4 space-y-3">
                  <div className="h-4 w-[92%] rounded-full bg-zinc-200" />
                  <div className="h-4 w-[88%] rounded-full bg-zinc-200" />
                  <div className="h-4 w-[80%] rounded-full bg-zinc-200" />
                </div>
              </div>
            ))}
          </div>

          {/* FAQ skeleton */}
          <div className="mt-12">
            <div className="h-6 w-24 rounded-lg bg-zinc-200" />
            <div className="mt-4 space-y-3">
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="rounded-2xl border border-seekle-border bg-white p-5"
                >
                  <div className="h-4 w-64 rounded-full bg-zinc-200" />
                  <div className="mt-4 h-4 w-[90%] rounded-full bg-zinc-200" />
                </div>
              ))}
            </div>
          </div>

          {/* Footer skeleton */}
          <div className="mt-12 text-center">
            <div className="mx-auto h-3 w-72 rounded-full bg-zinc-200" />
            <div className="mx-auto mt-3 h-3 w-32 rounded-full bg-zinc-200" />
          </div>
        </div>
      </div>
    </main>
  );
}
