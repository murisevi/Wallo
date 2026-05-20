export default function ReportsLoading() {
  return (
    <div className="space-y-6">
      {/* Header + controls skeleton */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="h-8 w-36 animate-pulse rounded-full bg-[#f3f4f3]" />
            <div className="mt-2 h-4 w-72 animate-pulse rounded-full bg-[#edeeed]" />
          </div>
          {/* Period selector skeleton */}
          <div className="h-9 w-64 animate-pulse rounded-full bg-[#f3f4f3]" />
        </div>
        {/* Date navigator skeleton */}
        <div className="h-14 animate-pulse rounded-xl bg-white shadow-sm" />
      </div>

      {/* Balance evolution — full width */}
      <div className="rounded-xl bg-white p-6 shadow-sm">
        <div className="mb-4 h-5 w-52 animate-pulse rounded-full bg-[#f3f4f3]" />
        <div className="h-80 animate-pulse rounded-lg bg-[#f3f4f3]" />
      </div>

      {/* Two-column: spending donut + income donut */}
      <div className="grid gap-6 lg:grid-cols-2">
        {[0, 1].map((i) => (
          <div key={i} className="rounded-xl bg-white p-6 shadow-sm">
            <div className="mb-4 h-5 w-40 animate-pulse rounded-full bg-[#f3f4f3]" />
            <div className="h-72 animate-pulse rounded-lg bg-[#f3f4f3]" />
          </div>
        ))}
      </div>

      {/* Income vs expenses line chart — full width */}
      <div className="rounded-xl bg-white p-6 shadow-sm">
        <div className="mb-4 h-5 w-44 animate-pulse rounded-full bg-[#f3f4f3]" />
        <div className="h-72 animate-pulse rounded-lg bg-[#f3f4f3]" />
      </div>

      {/* Sankey — full width */}
      <div className="rounded-xl bg-white p-6 shadow-sm">
        <div className="mb-4 h-5 w-32 animate-pulse rounded-full bg-[#f3f4f3]" />
        <div className="h-[420px] animate-pulse rounded-lg bg-[#f3f4f3]" />
      </div>
    </div>
  );
}
