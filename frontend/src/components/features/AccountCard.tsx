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
    <div className="flex flex-col rounded-2xl bg-white p-5 shadow-card-md transition-shadow hover:shadow-card-lg">
      {/* Header row: bank name + currency badge */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-[#303333]">{account.bank_name}</p>
          {account.name && (
            <p className="mt-0.5 truncate text-xs text-[#5d605f]">{account.name}</p>
          )}
        </div>
        <span className="shrink-0 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700">
          {account.currency}
        </span>
      </div>

      {/* Masked IBAN */}
      <p className="mt-3 font-mono text-xs tracking-widest text-[#5d605f]">
        {maskIban(account.iban)}
      </p>

      {/* Balance */}
      <p
        className={`mt-4 text-2xl font-extrabold tabular-nums ${
          isPositive ? 'text-[#303333]' : 'text-red-500'
        }`}
      >
        {balance}
      </p>
    </div>
  );
}
