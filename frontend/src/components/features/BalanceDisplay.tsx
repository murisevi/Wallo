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
    <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-amber-400 via-amber-500 to-amber-600 px-8 py-12 text-center shadow-[0_8px_32px_rgba(245,158,11,0.25)]">
      {/* Decorative rings */}
      <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/10" />
      <div className="pointer-events-none absolute -bottom-24 -left-24 h-80 w-80 rounded-full bg-white/5" />

      <p className="relative text-xs font-bold uppercase tracking-[0.22em] text-amber-100">
        Dinero libre disponible
      </p>

      <p className="relative mt-4 text-6xl font-extrabold tabular-nums text-white drop-shadow-sm lg:text-7xl">
        {formatted}
      </p>

      <p className="relative mt-4 text-sm text-amber-200">
        {accountCount === 0
          ? 'Conecta tu banco para ver tus saldos'
          : accountCount === 1
            ? 'En 1 cuenta conectada'
            : `En ${accountCount} cuentas conectadas`}
      </p>
    </div>
  );
}
