export default function ConnectLoading() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header skeleton */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 animate-pulse rounded-lg bg-gray-100" />
        <div className="space-y-1.5">
          <div className="h-5 w-36 animate-pulse rounded-full bg-gray-200" />
          <div className="h-3 w-52 animate-pulse rounded-full bg-gray-100" />
        </div>
      </div>

      {/* Search skeleton */}
      <div className="h-10 animate-pulse rounded-xl bg-gray-100" />

      {/* Bank grid skeleton */}
      <div className="grid gap-3 sm:grid-cols-2">
        {Array.from({ length: 6 }, (_, i) => (
          <div
            key={i}
            className="flex animate-pulse items-center gap-4 rounded-xl border border-gray-200 bg-white px-4 py-4"
          >
            <div className="h-9 w-9 rounded-lg bg-gray-100" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-32 rounded-full bg-gray-200" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
