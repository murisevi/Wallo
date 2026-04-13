export default function DashboardLoading() {
  return (
    <div className="space-y-8">
      {/* Greeting skeleton */}
      <div>
        <div className="h-8 w-48 animate-pulse rounded-full bg-[#f3f4f3]" />
        <div className="mt-2 h-4 w-64 animate-pulse rounded-full bg-[#edeeed]" />
      </div>

      {/* Balance hero skeleton */}
      <div className="animate-pulse rounded-3xl bg-amber-100 px-8 py-12 text-center">
        <div className="mx-auto h-3 w-40 rounded-full bg-amber-200" />
        <div className="mx-auto mt-5 h-16 w-72 rounded-2xl bg-amber-200" />
        <div className="mx-auto mt-4 h-3 w-48 rounded-full bg-amber-200" />
      </div>

      {/* Two-column skeleton */}
      <div className="grid gap-6 lg:grid-cols-2">
        {[0, 1].map((i) => (
          <div
            key={i}
            className="animate-pulse rounded-2xl bg-white p-6 shadow-[0_4px_16px_rgba(48,51,51,0.06)]"
          >
            <div className="mb-4 h-5 w-36 rounded-full bg-[#f3f4f3]" />
            <div className="h-24 w-full rounded-xl bg-[#f3f4f3]" />
          </div>
        ))}
      </div>
    </div>
  );
}
