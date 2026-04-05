interface BalanceDisplayProps {
  amount: string;
  currency: string;
  accountCount: number;
}

function formatCurrency(amount: string, currency: string): string {
  const num = parseFloat(amount);
  if (isNaN(num)) return '—';
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

export function BalanceDisplay({ amount, currency, accountCount }: BalanceDisplayProps) {
  const formatted = formatCurrency(amount, currency);

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-amber-400 via-amber-500 to-amber-600 px-6 py-10 text-center shadow-lg sm:py-14">
      {/* Decorative rings */}
      <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-white/5" />
      <div className="pointer-events-none absolute -bottom-20 -left-20 h-72 w-72 rounded-full bg-white/5" />

      <p className="relative text-xs font-semibold uppercase tracking-[0.2em] text-amber-100">
        Dinero Libre Disponible
      </p>

      <p className="relative mt-4 text-5xl font-extrabold tabular-nums text-white drop-shadow-sm sm:text-6xl lg:text-7xl">
        {formatted}
      </p>

      <p className="relative mt-4 text-sm text-amber-200">
        {accountCount === 0
          ? 'Sin cuentas conectadas'
          : accountCount === 1
            ? 'En 1 cuenta conectada'
            : `En ${accountCount} cuentas conectadas`}
      </p>
    </div>
  );
}
