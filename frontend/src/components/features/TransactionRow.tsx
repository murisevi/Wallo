import { CreditCard, TrendingUp } from 'lucide-react';
import type { Transaction } from '@/types';
import { CategoryBadge } from './CategoryBadge';

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

  // Use category color for the icon circle when available
  const catColor = transaction.category?.color ?? null;
  const Icon = isCredit ? TrendingUp : CreditCard;

  return (
    <div className="flex items-center gap-3 py-3 rounded-xl px-2 hover:bg-[#faf9f8] transition-colors">
      {/* Category icon circle — tinted with actual category color */}
      <div
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
        style={
          catColor
            ? { backgroundColor: `${catColor}25` }
            : { backgroundColor: isCredit ? '#d1fae5' : '#f3f4f3' }
        }
      >
        <Icon
          size={17}
          style={catColor ? { color: catColor } : undefined}
          className={catColor ? undefined : isCredit ? 'text-[#216c36]' : 'text-[#5d605f]'}
        />
      </div>

      {/* Label + category badge + date */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-[#303333]">{label}</p>
        <div className="mt-0.5 flex items-center gap-1.5">
          {transaction.category ? (
            <CategoryBadge
              name={transaction.category.name}
              color={transaction.category.color}
              confidence={transaction.confidence_score}
              method={transaction.categorization_method}
            />
          ) : transaction.category_name ? (
            <span className="rounded-full bg-[#f3f4f3] px-2 py-0.5 text-xs font-medium text-[#5d605f]">
              {transaction.category_name}
            </span>
          ) : null}
          <span className="text-xs text-[#5d605f]">{formattedDate}</span>
        </div>
      </div>

      {/* Amount */}
      <span
        className={`shrink-0 text-sm font-bold tabular-nums ${
          isCredit ? 'text-[#216c36]' : 'text-red-500'
        }`}
      >
        {isCredit ? '+ ' : '- '}
        {formattedAmount}
      </span>
    </div>
  );
}
