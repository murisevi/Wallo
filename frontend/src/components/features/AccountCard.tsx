import type { AccountSummary } from '@/types';

interface AccountCardProps {
  account: AccountSummary;
}

function maskIban(iban: string | null): string {
  if (!iban) return '—';
  return `**** ${iban.slice(-4)}`;
}

export function AccountCard({ account }: AccountCardProps) {
  const balance =
    account.balance != null
      ? new Intl.NumberFormat('es-ES', {
          style: 'currency',
          currency: account.currency,
          minimumFractionDigits: 2,
        }).format(parseFloat(account.balance))
      : '—';

  const isPositive = account.balance != null && parseFloat(account.balance) >= 0;

  return (
    <div className="flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      {/* Header row: bank name + currency badge */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-gray-900">{account.bank_name}</p>
          {account.name && (
            <p className="mt-0.5 truncate text-xs text-gray-500">{account.name}</p>
          )}
        </div>
        <span className="shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 ring-1 ring-amber-200">
          {account.currency}
        </span>
      </div>

      {/* Masked IBAN */}
      <p className="mt-2 font-mono text-xs tracking-widest text-gray-400">
        {maskIban(account.iban)}
      </p>

      {/* Balance */}
      <p
        className={`mt-4 text-2xl font-bold tabular-nums ${
          isPositive ? 'text-gray-900' : 'text-red-500'
        }`}
      >
        {balance}
      </p>
    </div>
  );
}
