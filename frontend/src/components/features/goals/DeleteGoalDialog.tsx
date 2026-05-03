import type { SavingsGoal } from '@/types/goals';

interface DeleteGoalDialogProps {
  goal: SavingsGoal;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const fmt = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });

export function DeleteGoalDialog({
  goal,
  onConfirm,
  onCancel,
  isLoading,
}: DeleteGoalDialogProps) {
  const hasSavings = parseFloat(goal.current_amount) > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-[#303333]">Eliminar objetivo</h3>
        <p className="mt-2 text-sm text-[#5d605f]">
          {hasSavings
            ? `¿Eliminar "${goal.name}"? Tienes ${fmt.format(parseFloat(goal.current_amount))} acumulados en este objetivo. Esta acción no se puede deshacer.`
            : `¿Eliminar "${goal.name}"? Esta acción no se puede deshacer.`}
        </p>
        <div className="mt-5 flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 rounded-xl border border-[#edeeed] py-2.5 text-sm font-medium text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="flex-1 rounded-xl bg-red-500 py-2.5 text-sm font-semibold text-white hover:bg-red-600 disabled:opacity-50 transition-colors"
          >
            {isLoading ? 'Eliminando...' : 'Eliminar'}
          </button>
        </div>
      </div>
    </div>
  );
}
