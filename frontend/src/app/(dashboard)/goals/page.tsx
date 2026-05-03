'use client';

import { useState } from 'react';
import { Plus, ChevronDown, ChevronUp } from 'lucide-react';
import { useGoals, useCreateGoal, useUpdateGoal, useDeleteGoal, useAddContribution } from '@/hooks/useGoals';
import { GoalSummaryCard } from '@/components/features/goals/GoalSummaryCard';
import { GoalCard } from '@/components/features/goals/GoalCard';
import { GoalEmptyState } from '@/components/features/goals/GoalEmptyState';
import { NewGoalModal } from '@/components/features/goals/NewGoalModal';
import { EditGoalModal } from '@/components/features/goals/EditGoalModal';
import { DeleteGoalDialog } from '@/components/features/goals/DeleteGoalDialog';
import type { GoalCreate, GoalUpdate, SavingsGoal } from '@/types/goals';

export default function GoalsPage() {
  const { data: summary, isLoading, isError } = useGoals();
  const createGoal = useCreateGoal();
  const updateGoal = useUpdateGoal();
  const deleteGoal = useDeleteGoal();
  const addContribution = useAddContribution();

  const [showNewModal, setShowNewModal] = useState(false);
  const [editingGoal, setEditingGoal] = useState<SavingsGoal | null>(null);
  const [deletingGoal, setDeletingGoal] = useState<SavingsGoal | null>(null);
  const [completedExpanded, setCompletedExpanded] = useState(false);

  if (isLoading) return null;

  if (isError) {
    return (
      <div className="py-20 text-center text-sm text-red-500">
        Error al cargar los objetivos. Inténtalo de nuevo.
      </div>
    );
  }

  const activeGoals = summary?.goals.filter((g) => g.status === 'active') ?? [];
  const completedGoals = summary?.goals.filter((g) => g.status !== 'active') ?? [];
  const hasGoals = (summary?.goals.length ?? 0) > 0;

  function handleCreate(data: GoalCreate) {
    createGoal.mutate(data, { onSuccess: () => setShowNewModal(false) });
  }

  function handleUpdate(id: string, data: GoalUpdate) {
    updateGoal.mutate({ id, data }, { onSuccess: () => setEditingGoal(null) });
  }

  function handleMarkCompleted(id: string) {
    updateGoal.mutate(
      { id, data: { status: 'completed' } },
      { onSuccess: () => setEditingGoal(null) },
    );
  }

  function handleDelete() {
    if (!deletingGoal) return;
    deleteGoal.mutate(deletingGoal.id, { onSuccess: () => setDeletingGoal(null) });
  }

  function handleContribute(id: string, amount: number, note: string | null) {
    addContribution.mutate({ id, data: { amount, note } });
  }

  return (
    <div className="space-y-6 pb-32">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[#303333]">Objetivos de ahorro</h1>
        <button
          onClick={() => setShowNewModal(true)}
          className="flex items-center gap-2 rounded-full bg-[#0060ad] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#0052a3] transition-colors"
        >
          <Plus size={16} />
          Nuevo objetivo
        </button>
      </div>

      {!hasGoals ? (
        <GoalEmptyState onCreateClick={() => setShowNewModal(true)} />
      ) : (
        <>
          {summary && (
            <GoalSummaryCard
              summary={summary}
              completedExpanded={completedExpanded}
              onToggleCompleted={() => setCompletedExpanded((p) => !p)}
            />
          )}

          {activeGoals.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#9ca3af]">
                Objetivos activos
              </h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {activeGoals.map((goal) => (
                  <GoalCard
                    key={goal.id}
                    goal={goal}
                    onContribute={handleContribute}
                    onEdit={setEditingGoal}
                    onDelete={setDeletingGoal}
                    isContributing={addContribution.isPending}
                  />
                ))}
              </div>
            </section>
          )}

          {completedGoals.length > 0 && (
            <section>
              <button
                onClick={() => setCompletedExpanded((p) => !p)}
                className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-[#9ca3af] hover:text-[#5d605f] transition-colors"
              >
                Completados ({completedGoals.length})
                {completedExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
              {completedExpanded && (
                <div className="grid grid-cols-1 gap-4 opacity-75 md:grid-cols-2 lg:grid-cols-3">
                  {completedGoals.map((goal) => (
                    <GoalCard
                      key={goal.id}
                      goal={goal}
                      onContribute={handleContribute}
                      onEdit={setEditingGoal}
                      onDelete={setDeletingGoal}
                    />
                  ))}
                </div>
              )}
            </section>
          )}
        </>
      )}

      {showNewModal && (
        <NewGoalModal
          onSubmit={handleCreate}
          onCancel={() => setShowNewModal(false)}
          isLoading={createGoal.isPending}
        />
      )}
      {editingGoal && (
        <EditGoalModal
          goal={editingGoal}
          onSubmit={handleUpdate}
          onMarkCompleted={handleMarkCompleted}
          onCancel={() => setEditingGoal(null)}
          isLoading={updateGoal.isPending}
        />
      )}
      {deletingGoal && (
        <DeleteGoalDialog
          goal={deletingGoal}
          onConfirm={handleDelete}
          onCancel={() => setDeletingGoal(null)}
          isLoading={deleteGoal.isPending}
        />
      )}
    </div>
  );
}
