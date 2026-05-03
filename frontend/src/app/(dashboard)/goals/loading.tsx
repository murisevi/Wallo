export default function GoalsLoading() {
  return (
    <div className="space-y-6 pb-32">
      <div className="flex items-center justify-between">
        <div className="h-8 w-52 animate-pulse rounded-full bg-[#f3f4f3]" />
        <div className="h-11 w-44 animate-pulse rounded-full bg-[#f3f4f3]" />
      </div>

      <div className="animate-pulse rounded-2xl bg-white p-5 shadow-card">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-3 w-24 rounded-full bg-[#edeeed]" />
            <div className="h-9 w-40 rounded-full bg-[#f3f4f3]" />
            <div className="mt-3 h-2.5 w-72 rounded-full bg-[#edeeed]" />
          </div>
          <div className="space-y-2 text-right">
            <div className="h-7 w-10 rounded-full bg-[#edeeed]" />
            <div className="h-3 w-12 rounded-full bg-[#edeeed]" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }, (_, i) => (
          <div
            key={i}
            className="animate-pulse overflow-hidden rounded-2xl bg-white shadow-card"
            style={{ borderLeft: '4px solid #f3f4f3' }}
          >
            <div className="p-4 space-y-3">
              <div className="flex items-center gap-2">
                <div className="h-5 w-5 rounded-full bg-[#edeeed]" />
                <div className="h-4 w-32 rounded-full bg-[#f3f4f3]" />
              </div>
              <div className="h-3 w-full rounded-full bg-[#edeeed]" />
              <div className="space-y-1">
                <div className="h-3 w-2/3 rounded-full bg-[#edeeed]" />
                <div className="h-2.5 rounded-full bg-[#f3f4f3]" />
              </div>
              <div className="h-9 w-full rounded-xl bg-[#f3f4f3]" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
