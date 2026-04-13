'use client';

import { useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Pencil,
  Trash2,
  ShoppingCart,
  Utensils,
  Car,
  Home,
  Heart,
  Shirt,
  BookOpen,
  Repeat,
  HelpCircle,
  X,
} from 'lucide-react';
import {
  useBudgetSummary,
  useBudgetCategories,
  useCreateBudget,
  useUpdateBudget,
  useDeleteBudget,
} from '@/hooks/useBudgets';
import type { Budget, BudgetUpdate, Category } from '@/types/budget';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

function formatEur(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(num);
}

const ICON_MAP: Record<string, React.ElementType> = {
  'shopping-cart': ShoppingCart,
  utensils: Utensils,
  car: Car,
  home: Home,
  heart: Heart,
  shirt: Shirt,
  book: BookOpen,
  repeat: Repeat,
};

const CATEGORY_COLORS: Record<string, { bg: string; icon: string }> = {
  'shopping-cart': { bg: 'bg-green-100', icon: 'text-green-600' },
  utensils:        { bg: 'bg-amber-100', icon: 'text-amber-600' },
  car:             { bg: 'bg-red-100',   icon: 'text-red-500' },
  home:            { bg: 'bg-blue-100',  icon: 'text-blue-600' },
  heart:           { bg: 'bg-pink-100',  icon: 'text-pink-500' },
  shirt:           { bg: 'bg-purple-100',icon: 'text-purple-600' },
  book:            { bg: 'bg-indigo-100',icon: 'text-indigo-600' },
  repeat:          { bg: 'bg-violet-100',icon: 'text-violet-600' },
};

function CategoryIcon({ icon, size = 16 }: { icon: string; size?: number }) {
  const Icon = ICON_MAP[icon] ?? HelpCircle;
  return <Icon size={size} />;
}

function progressBarColor(pct: number): string {
  if (pct >= 100) return 'bg-red-500';
  if (pct >= 80) return 'bg-yellow-500';
  return 'bg-green-500';
}

function statusBadgeClass(status: string): string {
  if (status === 'SUPERADO') return 'bg-red-100 text-red-700';
  if (status === 'CERCA DEL LÍMITE') return 'bg-yellow-100 text-yellow-700';
  return 'bg-green-100 text-green-700';
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-gray-200 ${className ?? ''}`} />;
}

function BudgetSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-36 w-full" />
      <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    </div>
  );
}

// ─── Budget category card ─────────────────────────────────────────────────────

function BudgetCard({ budget }: { budget: Budget }) {
  const pct = Math.min(budget.percentage, 100);
  const colors = CATEGORY_COLORS[budget.category_icon] ?? {
    bg: 'bg-gray-100',
    icon: 'text-gray-500',
  };

  return (
    <div className="rounded-2xl bg-white p-4 shadow-[0_2px_8px_rgba(48,51,51,0.06)]">
      <div className="flex items-center gap-3">
        {/* Category icon */}
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${colors.bg}`}
        >
          <span className={colors.icon}>
            <CategoryIcon icon={budget.category_icon} size={18} />
          </span>
        </div>

        {/* Name + amounts */}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-[#303333]">{budget.category_name}</p>
          <p className="text-xs text-[#5d605f]">
            Gastado {formatEur(budget.amount_spent)} / {formatEur(budget.amount_limit)}
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-3">
        <div className="mb-1 flex items-center justify-between">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
            <div
              className={`h-full rounded-full transition-all ${progressBarColor(budget.percentage)}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="ml-3 shrink-0 text-xs font-semibold text-[#5d605f]">
            {budget.percentage.toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Modal: New budget ────────────────────────────────────────────────────────

interface NewBudgetModalProps {
  month: number;
  year: number;
  usedCategoryIds: Set<string>;
  onClose: () => void;
}

function NewBudgetModal({ month, year, usedCategoryIds, onClose }: NewBudgetModalProps) {
  const { data: categories = [] } = useBudgetCategories();
  const createMutation = useCreateBudget();

  const [categoryId, setCategoryId] = useState('');
  const [limit, setLimit] = useState('');
  const [error, setError] = useState('');

  const availableCategories = categories.filter(
    (c: Category) => !usedCategoryIds.has(c.id),
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const parsedLimit = parseFloat(limit.replace(',', '.'));
    if (!categoryId) { setError('Selecciona una categoría.'); return; }
    if (isNaN(parsedLimit) || parsedLimit <= 0) { setError('Introduce un límite válido mayor que 0.'); return; }

    try {
      await createMutation.mutateAsync({
        category_id: categoryId,
        amount_limit: parsedLimit,
        month,
        year,
      });
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al crear el presupuesto.');
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        {/* Header */}
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-extrabold text-[#303333]">Nuevo Presupuesto</h2>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Category select */}
          <div>
            <label className="mb-1.5 block text-xs font-bold uppercase tracking-widest text-[#5d605f]">
              Categoría
            </label>
            {availableCategories.length === 0 ? (
              <p className="rounded-xl bg-[#f3f4f3] px-4 py-3 text-sm text-[#5d605f]">
                Ya tienes presupuesto en todas las categorías para este mes.
              </p>
            ) : (
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="w-full rounded-xl border border-[#e8e9e8] bg-[#f3f4f3] px-4 py-2.5 text-sm text-[#303333] outline-none focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
              >
                <option value="">Selecciona una categoría…</option>
                {availableCategories.map((c: Category) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            )}
          </div>

          {/* Limit input */}
          <div>
            <label className="mb-1.5 block text-xs font-bold uppercase tracking-widest text-[#5d605f]">
              Límite mensual (€)
            </label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              placeholder="0,00"
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
              className="w-full rounded-xl border border-[#e8e9e8] bg-[#f3f4f3] px-4 py-2.5 text-sm text-[#303333] outline-none focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
            />
          </div>

          {error && <p className="text-xs font-medium text-red-600">{error}</p>}

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl bg-[#f3f4f3] py-2.5 text-sm font-semibold text-[#303333] hover:bg-[#edeeed] transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || availableCategories.length === 0}
              className="flex-1 rounded-xl bg-gradient-to-r from-[#0060ad] to-[#68abff] py-2.5 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50 transition-all"
            >
              {createMutation.isPending ? 'Creando…' : 'Crear Presupuesto'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Modal: Edit budgets ──────────────────────────────────────────────────────

interface EditBudgetsModalProps {
  budgets: Budget[];
  onClose: () => void;
}

function EditBudgetsModal({ budgets, onClose }: EditBudgetsModalProps) {
  const updateMutation = useUpdateBudget();
  const deleteMutation = useDeleteBudget();

  // Local state: budgetId → new limit string
  const [limits, setLimits] = useState<Record<string, string>>(
    Object.fromEntries(budgets.map((b) => [b.id, parseFloat(b.amount_limit).toFixed(2)])),
  );
  const [error, setError] = useState('');

  async function handleSave() {
    setError('');
    const updates = budgets
      .map((b) => {
        const parsed = parseFloat((limits[b.id] ?? '').replace(',', '.'));
        return { id: b.id, value: parsed };
      })
      .filter((u) => !isNaN(u.value) && u.value > 0);

    try {
      await Promise.all(
        updates.map(({ id, value }) =>
          updateMutation.mutateAsync({ id, data: { amount_limit: value } as BudgetUpdate }),
        ),
      );
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al guardar cambios.');
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteMutation.mutateAsync(id);
    } catch {
      // ignore individual delete errors silently
    }
  }

  const isPending = updateMutation.isPending || deleteMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        {/* Header */}
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-extrabold text-[#303333]">Editar Presupuestos</h2>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
          {budgets.length === 0 && (
            <p className="py-4 text-center text-sm text-[#5d605f]">
              No hay presupuestos para editar.
            </p>
          )}
          {budgets.map((b) => {
            const colors = CATEGORY_COLORS[b.category_icon] ?? { bg: 'bg-gray-100', icon: 'text-gray-500' };
            return (
              <div
                key={b.id}
                className="flex items-center gap-3 rounded-xl border border-[#f3f4f3] p-3"
              >
                <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${colors.bg}`}>
                  <span className={colors.icon}>
                    <CategoryIcon icon={b.category_icon} size={15} />
                  </span>
                </div>
                <span className="min-w-0 flex-1 truncate text-sm font-semibold text-[#303333]">
                  {b.category_name}
                </span>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={limits[b.id] ?? ''}
                  onChange={(e) => setLimits((prev) => ({ ...prev, [b.id]: e.target.value }))}
                  className="w-24 rounded-lg border border-[#e8e9e8] bg-[#f3f4f3] px-3 py-1.5 text-right text-sm text-[#303333] outline-none focus:ring-2 focus:ring-[#0060ad]/20"
                />
                <span className="text-xs text-[#5d605f]">€</span>
                <button
                  onClick={() => handleDelete(b.id)}
                  disabled={isPending}
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-red-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40 transition-colors"
                  title="Eliminar presupuesto"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            );
          })}
        </div>

        {error && <p className="mt-3 text-xs font-medium text-red-600">{error}</p>}

        <div className="mt-5 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-xl bg-[#f3f4f3] py-2.5 text-sm font-semibold text-[#303333] hover:bg-[#edeeed] transition-colors"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={isPending || budgets.length === 0}
            className="flex-1 rounded-xl bg-gradient-to-r from-[#0060ad] to-[#68abff] py-2.5 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50 transition-all"
          >
            {updateMutation.isPending ? 'Guardando…' : 'Guardar Cambios'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function BudgetsPage() {
  const today = new Date();
  const [month, setMonth] = useState(today.getMonth() + 1); // 1-based
  const [year, setYear] = useState(today.getFullYear());
  const [showNewModal, setShowNewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);

  const { data, isLoading, isError, refetch } = useBudgetSummary(month, year);

  function prevMonth() {
    if (month === 1) { setMonth(12); setYear((y) => y - 1); }
    else setMonth((m) => m - 1);
  }

  function nextMonth() {
    if (month === 12) { setMonth(1); setYear((y) => y + 1); }
    else setMonth((m) => m + 1);
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
            onClick={prevMonth}
            className="flex h-7 w-7 items-center justify-center rounded-full text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="min-w-[130px] text-center text-sm font-semibold text-[#303333]">
            {MONTH_NAMES[month - 1]} {year}
          </span>
          <button
            onClick={nextMonth}
            className="flex h-7 w-7 items-center justify-center rounded-full text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* Error */}
      {isError && (
        <div className="rounded-2xl bg-white px-6 py-8 text-center shadow-[0_4px_16px_rgba(48,51,51,0.06)]">
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
          {/* ── Global summary card ── */}
          <div className="rounded-2xl bg-gray-50 p-5 shadow-[0_2px_12px_rgba(48,51,51,0.06)]">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-stretch">
              {/* Left: total spent + progress */}
              <div className="flex-1 space-y-3">
                <div>
                  <p className="text-xs font-semibold text-[#5d605f]">Gasto Total</p>
                  <div className="mt-0.5 flex items-center gap-3">
                    <span className="text-3xl font-extrabold tracking-tight text-[#303333]">
                      {formatEur(data.total_spent)}
                    </span>
                    <span
                      className={`rounded-full px-3 py-0.5 text-xs font-bold ${statusBadgeClass(data.status)}`}
                    >
                      {data.status}
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                {data.total_limit !== '0' && parseFloat(data.total_limit) > 0 && (
                  <div>
                    <div className="mb-1 flex items-center justify-between text-xs text-[#5d605f]">
                      <span>Progreso mensual</span>
                      <span className="font-semibold">
                        {data.percentage.toFixed(0)}% de {formatEur(data.total_limit)}
                      </span>
                    </div>
                    <div className="h-3 overflow-hidden rounded-full bg-gray-200">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] transition-all"
                        style={{ width: `${Math.min(data.percentage, 100)}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Right: available + message */}
              <div className="shrink-0 rounded-xl border border-[#e8e9e8] bg-white p-4 sm:w-64">
                <p className="text-xs font-semibold text-[#5d605f]">Disponible</p>
                <p className="mt-0.5 text-2xl font-extrabold text-green-600">
                  +{formatEur(data.total_available)}
                </p>
                <p className="mt-2 text-xs leading-relaxed text-[#5d605f]">
                  {data.comparison_message}
                </p>
              </div>
            </div>
          </div>

          {/* ── Category list ── */}
          <div>
            <h2 className="mb-3 text-base font-extrabold text-[#303333]">Categorías</h2>

            {data.budgets.length === 0 ? (
              <div className="rounded-2xl bg-white px-6 py-14 text-center shadow-[0_2px_8px_rgba(48,51,51,0.06)]">
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
                  <BudgetCard key={b.id} budget={b} />
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* ── Floating Action Buttons ── */}
      <div className="fixed bottom-8 right-6 flex flex-col items-end gap-3">
        {/* Edit */}
        <button
          onClick={() => setShowEditModal(true)}
          className="flex items-center gap-2 rounded-full border border-[#e8e9e8] bg-white px-5 py-3 text-sm font-semibold text-[#303333] shadow-lg hover:bg-[#f3f4f3] transition-colors"
        >
          <Pencil size={15} />
          Editar Presupuestos
        </button>

        {/* New */}
        <button
          onClick={() => setShowNewModal(true)}
          className="flex items-center gap-2 rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] px-5 py-3 text-sm font-bold text-white shadow-lg hover:opacity-90 transition-all"
        >
          <Plus size={15} />
          Nuevo Presupuesto
        </button>
      </div>

      {/* ── Modals ── */}
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
