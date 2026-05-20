'use client';

import { useState } from 'react';
import { X, Trash2 } from 'lucide-react';
import {
  ShoppingCart, Utensils, Car, Home, Heart, Shirt, BookOpen, Repeat, HelpCircle,
} from 'lucide-react';
import { useUpdateBudget, useDeleteBudget } from '@/hooks/useBudgets';
import type { Budget, BudgetUpdate } from '@/types/budget';

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
  'shopping-cart': { bg: 'bg-green-100',  icon: 'text-green-600' },
  utensils:        { bg: 'bg-amber-100',  icon: 'text-amber-600' },
  car:             { bg: 'bg-red-100',    icon: 'text-red-500' },
  home:            { bg: 'bg-blue-100',   icon: 'text-blue-600' },
  heart:           { bg: 'bg-pink-100',   icon: 'text-pink-500' },
  shirt:           { bg: 'bg-purple-100', icon: 'text-purple-600' },
  book:            { bg: 'bg-indigo-100', icon: 'text-indigo-600' },
  repeat:          { bg: 'bg-violet-100', icon: 'text-violet-600' },
};

interface EditBudgetsModalProps {
  budgets: Budget[];
  onClose: () => void;
}

export function EditBudgetsModal({ budgets, onClose }: EditBudgetsModalProps) {
  const updateMutation = useUpdateBudget();
  const deleteMutation = useDeleteBudget();

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
            const Icon = ICON_MAP[b.category_icon] ?? HelpCircle;
            return (
              <div
                key={b.id}
                className="flex items-center gap-3 rounded-xl border border-[#f3f4f3] p-3"
              >
                <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${colors.bg}`}>
                  <Icon size={15} className={colors.icon} />
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
