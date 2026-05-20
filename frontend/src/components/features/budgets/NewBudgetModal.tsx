'use client';

import { useState } from 'react';
import { X } from 'lucide-react';
import { useBudgetCategories, useCreateBudget } from '@/hooks/useBudgets';
import type { Category } from '@/types/budget';

interface NewBudgetModalProps {
  month: number;
  year: number;
  usedCategoryIds: Set<string>;
  onClose: () => void;
}

export function NewBudgetModal({ month, year, usedCategoryIds, onClose }: NewBudgetModalProps) {
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
