function SectionSkeleton({ rows = 2 }: { rows?: number }) {
  return (
    <div className="animate-pulse rounded-2xl bg-white p-6 shadow-card">
      <div className="mb-5 h-4 w-36 rounded-full bg-[#f3f4f3]" />
      <div className="space-y-3">
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} className="h-11 w-full rounded-xl bg-[#f3f4f3]" />
        ))}
      </div>
    </div>
  );
}

export default function SettingsLoading() {
  return (
    <div className="mx-auto max-w-2xl space-y-5">
      {/* Title */}
      <div>
        <div className="h-8 w-44 animate-pulse rounded-full bg-[#f3f4f3]" />
        <div className="mt-2 h-4 w-80 animate-pulse rounded-full bg-[#edeeed]" />
      </div>

      {/* Perfil Personal: 2 inputs + button */}
      <div className="animate-pulse rounded-2xl bg-white p-6 shadow-card">
        <div className="mb-5 h-4 w-36 rounded-full bg-[#f3f4f3]" />
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="h-11 rounded-xl bg-[#f3f4f3]" />
          <div className="h-11 rounded-xl bg-[#f3f4f3]" />
        </div>
        <div className="mt-4 h-11 w-full rounded-xl bg-[#f3f4f3]" />
        <div className="mt-4 flex justify-end">
          <div className="h-10 w-36 rounded-xl bg-[#edeeed]" />
        </div>
      </div>

      {/* Cuentas conectadas */}
      <SectionSkeleton rows={3} />

      {/* Sesion */}
      <SectionSkeleton rows={1} />
    </div>
  );
}
