'use client';

import { Copy, X } from 'lucide-react';
import type { CopySource } from '@/types/budget';

const MONTH_NAMES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];

function formatEur(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(num);
}

interface CopyBudgetBannerProps {
  /** Target month (1-12) */
  month: number;
  /** Source month data returned by /budgets/copy-source */
  copySource: CopySource;
  /** Whether the copy mutation is in progress */
  isCopying: boolean;
  /** Callback to confirm copy */
  onCopy: () => void;
  /** Callback to dismiss banner */
  onDismiss: () => void;
}

export function CopyBudgetBanner({
  month,
  copySource,
  isCopying,
  onCopy,
  onDismiss,
}: CopyBudgetBannerProps) {
  const sourceMonthName = MONTH_NAMES[copySource.month - 1];
  const currentMonthName = MONTH_NAMES[month - 1];
  const count = copySource.budget_count;
  const total = copySource.total_limit;

  return (
    <div className="flex items-start gap-4 rounded-2xl border border-[#0060ad]/20 bg-[#e8f0f8] p-5">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#0060ad]/10">
        <Copy size={18} className="text-[#0060ad]" />
      </div>

      <div className="flex-1">
        <p className="text-sm font-bold text-[#303333]">
          No tienes presupuestos para {currentMonthName}.
        </p>
        <p className="mt-0.5 text-xs text-[#5d605f]">
          ¿Copiar los de {sourceMonthName}?{' '}
          <span className="font-semibold">
            {count} {count === 1 ? 'categoría' : 'categorías'},{' '}
            {formatEur(total)} en total.
          </span>
        </p>

        <div className="mt-3 flex gap-2">
          <button
            onClick={onCopy}
            disabled={isCopying}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[#0060ad] px-4 py-2 text-xs font-bold text-white hover:opacity-90 disabled:opacity-50 transition-all"
          >
            <Copy size={12} />
            {isCopying ? 'Copiando…' : 'Copiar'}
          </button>
          <button
            onClick={onDismiss}
            className="rounded-xl bg-white px-4 py-2 text-xs font-semibold text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            Empezar desde cero
          </button>
        </div>
      </div>

      <button
        onClick={onDismiss}
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[#5d605f] hover:bg-[#0060ad]/10 transition-colors"
      >
        <X size={14} />
      </button>
    </div>
  );
}
