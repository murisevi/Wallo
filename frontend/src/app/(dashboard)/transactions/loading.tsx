export default function TransactionsLoading() {
  return (
    <div className="space-y-6">
      {/* Header skeleton */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 animate-pulse rounded-lg bg-gray-100" />
        <div className="h-6 w-40 animate-pulse rounded-full bg-gray-200" />
      </div>

      {/* Search skeleton */}
      <div className="h-10 animate-pulse rounded-xl bg-gray-100" />

      {/* Row skeletons */}
      <div className="rounded-xl border border-gray-200 bg-white px-5 divide-y divide-gray-100">
        {Array.from({ length: 10 }, (_, i) => (
          <div key={i} className="flex animate-pulse items-center justify-between gap-4 py-3.5">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-gray-100" />
              <div>
                <div className="h-4 w-40 rounded-full bg-gray-200" />
                <div className="mt-1.5 h-3 w-20 rounded-full bg-gray-100" />
              </div>
            </div>
            <div className="h-4 w-20 rounded-full bg-gray-200" />
          </div>
        ))}
      </div>
    </div>
  );
}
