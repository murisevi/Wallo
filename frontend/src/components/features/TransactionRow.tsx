import type { Transaction } from '@/types';

interface TransactionRowProps {
  transaction: Transaction;
}

export function TransactionRow({ transaction }: TransactionRowProps) {
  const isCredit = transaction.credit_debit_indicator === 'CRDT';
  const absAmount = Math.abs(parseFloat(transaction.amount));

  const formattedAmount = new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: transaction.currency,
    minimumFractionDigits: 2,
  }).format(absAmount);

  const label =
    transaction.description ??
    transaction.creditor_name ??
    transaction.debtor_name ??
    'Transacción';

  const formattedDate = new Date(transaction.date + 'T00:00:00').toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
  });

  return (
    <div className="flex items-center justify-between gap-4 py-3.5">
      {/* Left: icon + label + date */}
      <div className="flex min-w-0 items-center gap-3">
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
            isCredit
              ? 'bg-emerald-50 text-emerald-600'
              : 'bg-red-50 text-red-400'
          }`}
          aria-hidden="true"
        >
          {isCredit ? '+' : '−'}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-gray-900">{label}</p>
          <p className="text-xs text-gray-400">{formattedDate}</p>
        </div>
      </div>

      {/* Right: amount */}
      <span
        className={`shrink-0 text-sm font-semibold tabular-nums ${
          isCredit ? 'text-emerald-600' : 'text-red-500'
        }`}
      >
        {isCredit ? '+' : '−'}
        {formattedAmount}
      </span>
    </div>
  );
}
