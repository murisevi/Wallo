'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight, Plus, Pencil } from 'lucide-react';
import {
  useBudgetSummary,
  useCopyPreviousBudgets,
  useCopySource,
} from '@/hooks/useBudgets';
import { BudgetSummaryCard } from '@/components/features/budgets/BudgetSummaryCard';
import { BudgetCategoryCard } from '@/components/features/budgets/BudgetCategoryCard';
import { CopyBudgetBanner } from '@/components/features/budgets/CopyBudgetBanner';
import { NewBudgetModal } from '@/components/features/budgets/NewBudgetModal';
import { EditBudgetsModal } from '@/components/features/budgets/EditBudgetsModal';

const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-gray-200 ${className ?? ''}`} />;
}

function BudgetSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-36 w-full" />
      <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-20 w-full" />)}
      </div>
    </div>
  );
}

export default function BudgetsPage() {
  const today = new Date();
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [year, setYear] = useState(today.getFullYear());
  const [showNewModal, setShowNewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [dismissedCopy, setDismissedCopy] = useState(false);

  const { data, isLoading, isError, refetch } = useBudgetSummary(month, year);

  // Find the most recent previous month with budgets (up to 6 months back)
  const currentIsEmpty = !isLoading && !isError && (data?.budgets.length ?? 0) === 0;
  const { data: copySource } = useCopySource(month, year);

  const showCopyBanner = currentIsEmpty && !dismissedCopy && !!copySource;

  const copyMutation = useCopyPreviousBudgets();
  const [copyError, setCopyError] = useState('');

  function prevMonthNav() {
    if (month === 1) { setMonth(12); setYear((y) => y - 1); }
    else setMonth((m) => m - 1);
    setDismissedCopy(false);
    setCopyError('');
  }

  function nextMonthNav() {
    if (month === 12) { setMonth(1); setYear((y) => y + 1); }
    else setMonth((m) => m + 1);
    setDismissedCopy(false);
    setCopyError('');
  }

  async function handleCopy() {
    setCopyError('');
    try {
      await copyMutation.mutateAsync({ month, year });
    } catch (err: unknown) {
      setCopyError(err instanceof Error ? err.message : 'Error al copiar los presupuestos.');
    }
  }

  const usedCategoryIds = new Set(data?.budgets.map((b) => b.category_id) ?? []);

  return (
    <div className="relative space-y-6 pb-32">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
            Resumen Mensual
          </p>
          <h1 className="mt-0.5 text-3xl font-extrabold tracking-tight text-[#303333]">
            Presupuestos
          </h1>
        </div>

        {/* Month selector */}
        <div className="flex shrink-0 items-center gap-2 rounded-full border border-[#e8e9e8] bg-white px-3 py-2 shadow-sm">
          <button
            onClick={prevMonthNav}
            className="flex h-7 w-7 items-center justify-center rounded-full text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="min-w-[130px] text-center text-sm font-semibold text-[#303333]">
            {MONTH_NAMES[month - 1]} {year}
          </span>
          <button
            onClick={nextMonthNav}
            className="flex h-7 w-7 items-center justify-center rounded-full text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* Error */}
      {isError && (
        <div className="rounded-2xl bg-white px-6 py-8 text-center shadow-card-md">
          <p className="text-sm font-medium text-red-600">
            No se pudieron cargar los presupuestos.
          </p>
          <button
            onClick={() => refetch()}
            className="mt-3 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] px-5 py-2.5 text-sm font-bold text-white hover:opacity-90 transition-all"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Loading */}
      {isLoading && !isError && <BudgetSkeleton />}

      {/* Content */}
      {!isLoading && !isError && data && (
        <>
          {/* Resumen global */}
          {data.budgets.length > 0 && <BudgetSummaryCard data={data} />}

          {/* Banner copiar mes anterior */}
          {showCopyBanner && copySource && (
            <CopyBudgetBanner
              month={month}
              copySource={copySource}
              isCopying={copyMutation.isPending}
              onCopy={handleCopy}
              onDismiss={() => setDismissedCopy(true)}
            />
          )}
          {copyError && (
            <p className="rounded-xl bg-red-50 px-4 py-3 text-sm font-medium text-red-600">
              {copyError}
            </p>
          )}

          {/* Lista de categorías */}
          <div>
            <h2 className="mb-3 text-base font-extrabold text-[#303333]">Categorías</h2>

            {data.budgets.length === 0 && !showCopyBanner ? (
              <div className="rounded-2xl bg-white px-6 py-14 text-center shadow-card">
                <p className="text-sm text-[#5d605f]">
                  No tienes presupuestos para este mes.
                </p>
                <button
                  onClick={() => setShowNewModal(true)}
                  className="mt-4 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] px-5 py-2.5 text-sm font-bold text-white hover:opacity-90 transition-all"
                >
                  <Plus size={14} />
                  Crear tu primer presupuesto
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {data.budgets.map((b) => (
                  <BudgetCategoryCard key={b.id} budget={b} />
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* FABs */}
      <div className="fixed bottom-8 right-6 flex flex-col items-end gap-3">
        <button
          onClick={() => setShowEditModal(true)}
          className="flex items-center gap-2 rounded-full border border-[#e8e9e8] bg-white px-5 py-3 text-sm font-semibold text-[#303333] shadow-lg hover:bg-[#f3f4f3] transition-colors"
        >
          <Pencil size={15} />
          Editar Presupuestos
        </button>
        <button
          onClick={() => setShowNewModal(true)}
          className="flex items-center gap-2 rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] px-5 py-3 text-sm font-bold text-white shadow-lg hover:opacity-90 transition-all"
        >
          <Plus size={15} />
          Nuevo Presupuesto
        </button>
      </div>

      {/* Modales */}
      {showNewModal && (
        <NewBudgetModal
          month={month}
          year={year}
          usedCategoryIds={usedCategoryIds}
          onClose={() => setShowNewModal(false)}
        />
      )}
      {showEditModal && data && (
        <EditBudgetsModal
          budgets={data.budgets}
          onClose={() => setShowEditModal(false)}
        />
      )}
    </div>
  );
}
