export default function BudgetsLoading() {
  return (
    <div className="space-y-6 pb-32">
      {/* Header skeleton */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="h-3 w-28 animate-pulse rounded-full bg-[#edeeed]" />
          <div className="mt-2 h-8 w-48 animate-pulse rounded-full bg-[#f3f4f3]" />
        </div>
        <div className="h-11 w-44 animate-pulse rounded-full bg-[#f3f4f3]" />
      </div>

      {/* Summary card skeleton */}
      <div className="animate-pulse rounded-2xl bg-[#f3f4f3] p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-stretch">
          <div className="flex-1 space-y-3">
            <div className="h-3 w-20 rounded-full bg-[#edeeed]" />
            <div className="flex items-center gap-3">
              <div className="h-8 w-40 rounded-full bg-[#edeeed]" />
              <div className="h-5 w-20 rounded-full bg-[#edeeed]" />
            </div>
            <div className="h-3 rounded-full bg-[#edeeed]" />
            <div className="h-3 w-full rounded-full bg-[#edeeed]" />
          </div>
          <div className="h-24 w-full animate-none rounded-xl bg-[#edeeed] sm:w-64" />
        </div>
      </div>

      {/* Category budget cards skeleton */}
      <div>
        <div className="mb-3 h-5 w-28 animate-pulse rounded-full bg-[#f3f4f3]" />
        <div className="space-y-3">
          {Array.from({ length: 4 }, (_, i) => (
            <div
              key={i}
              className="animate-pulse rounded-2xl bg-white p-4 shadow-card"
            >
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-[#f3f4f3]" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-4 w-32 rounded-full bg-[#f3f4f3]" />
                  <div className="h-3 w-48 rounded-full bg-[#edeeed]" />
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2">
                <div className="h-2 flex-1 rounded-full bg-[#f3f4f3]" />
                <div className="h-3 w-8 rounded-full bg-[#edeeed]" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
