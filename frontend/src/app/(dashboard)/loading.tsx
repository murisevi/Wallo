export default function DashboardLoading() {
  return (
    <div className="space-y-8">
      {/* Balance hero skeleton */}
      <div className="animate-pulse rounded-2xl bg-amber-100 px-6 py-10 sm:py-14">
        <div className="mx-auto h-3 w-36 rounded-full bg-amber-200" />
        <div className="mx-auto mt-5 h-14 w-64 rounded-xl bg-amber-200" />
        <div className="mx-auto mt-4 h-3 w-40 rounded-full bg-amber-200" />
      </div>

      {/* Account cards skeleton */}
      <div>
        <div className="mb-3 h-4 w-32 animate-pulse rounded-full bg-gray-200" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="animate-pulse rounded-xl border border-gray-200 bg-white p-5"
            >
              <div className="flex justify-between">
                <div className="h-4 w-28 rounded-full bg-gray-200" />
                <div className="h-5 w-10 rounded-full bg-gray-100" />
              </div>
              <div className="mt-2 h-3 w-20 rounded-full bg-gray-100" />
              <div className="mt-4 h-7 w-32 rounded-lg bg-gray-200" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
