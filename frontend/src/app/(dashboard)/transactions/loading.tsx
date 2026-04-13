export default function TransactionsLoading() {
  return (
    <div className="space-y-6">
      {/* Header skeleton */}
      <div>
        <div className="h-8 w-44 animate-pulse rounded-full bg-[#f3f4f3]" />
        <div className="mt-2 h-4 w-24 animate-pulse rounded-full bg-[#edeeed]" />
      </div>

      {/* Search skeleton */}
      <div className="h-11 animate-pulse rounded-xl bg-[#f3f4f3]" />

      {/* Row skeletons */}
      <div className="rounded-2xl bg-white px-6 shadow-[0_4px_16px_rgba(48,51,51,0.06)]">
        {Array.from({ length: 10 }, (_, i) => (
          <div key={i} className="flex animate-pulse items-center justify-between gap-4 py-4 border-b border-[#f3f4f3] last:border-0">
            <div className="flex-1">
              <div className="h-4 w-40 rounded-full bg-[#f3f4f3]" />
              <div className="mt-1.5 h-3 w-20 rounded-full bg-[#edeeed]" />
            </div>
            <div className="h-4 w-20 rounded-full bg-[#f3f4f3]" />
          </div>
        ))}
      </div>
    </div>
  );
}
