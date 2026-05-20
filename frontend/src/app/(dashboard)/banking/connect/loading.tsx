export default function ConnectLoading() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      {/* Header skeleton */}
      <div className="space-y-2">
        <div className="h-8 w-48 animate-pulse rounded-full bg-[#f3f4f3]" />
        <div className="h-4 w-64 animate-pulse rounded-full bg-[#edeeed]" />
      </div>

      {/* Search skeleton */}
      <div className="h-11 animate-pulse rounded-xl bg-[#f3f4f3]" />

      {/* Bank grid skeleton */}
      <div className="grid gap-3 sm:grid-cols-2">
        {Array.from({ length: 6 }, (_, i) => (
          <div
            key={i}
            className="flex animate-pulse items-center gap-4 rounded-2xl bg-white px-5 py-4 shadow-card-md"
          >
            <div className="h-9 w-9 rounded-xl bg-[#f3f4f3]" />
            <div className="flex-1">
              <div className="h-4 w-32 rounded-full bg-[#f3f4f3]" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
