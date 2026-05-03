'use client';

import { useState } from 'react';
import {
  PiggyBank, Wallet, Home, Car, Plane, Heart, Star, Shield,
  GraduationCap, Laptop, Gift, Music, Camera, Book, Coffee,
  Sun, Umbrella, Anchor, Target, Trophy, X, type LucideIcon,
} from 'lucide-react';
import type { GoalUpdate, SavingsGoal } from '@/types/goals';

const ICONS: { name: string; Icon: LucideIcon }[] = [
  { name: 'piggy-bank', Icon: PiggyBank }, { name: 'wallet', Icon: Wallet },
  { name: 'home', Icon: Home }, { name: 'car', Icon: Car },
  { name: 'plane', Icon: Plane }, { name: 'heart', Icon: Heart },
  { name: 'star', Icon: Star }, { name: 'shield', Icon: Shield },
  { name: 'graduation-cap', Icon: GraduationCap }, { name: 'laptop', Icon: Laptop },
  { name: 'gift', Icon: Gift }, { name: 'music', Icon: Music },
  { name: 'camera', Icon: Camera }, { name: 'book', Icon: Book },
  { name: 'coffee', Icon: Coffee }, { name: 'sun', Icon: Sun },
  { name: 'umbrella', Icon: Umbrella }, { name: 'anchor', Icon: Anchor },
  { name: 'target', Icon: Target }, { name: 'trophy', Icon: Trophy },
];

const COLORS = [
  '#EF4444', '#F59E0B', '#F97316', '#10B981', '#3B82F6',
  '#6366F1', '#8B5CF6', '#EC4899', '#14B8A6', '#6B7280',
  '#84CC16', '#06B6D4',
];

interface EditGoalModalProps {
  goal: SavingsGoal;
  onSubmit: (id: string, data: GoalUpdate) => void;
  onMarkCompleted: (id: string) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function EditGoalModal({
  goal,
  onSubmit,
  onMarkCompleted,
  onCancel,
  isLoading,
}: EditGoalModalProps) {
  const [name, setName] = useState(goal.name);
  const [targetAmount, setTargetAmount] = useState(goal.target_amount);
  const [monthlyContribution, setMonthlyContribution] = useState(
    goal.monthly_contribution ?? '',
  );
  const [deadline, setDeadline] = useState(goal.deadline ?? '');
  const [icon, setIcon] = useState(goal.icon);
  const [color, setColor] = useState(goal.color);
  const [confirmComplete, setConfirmComplete] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const target = parseFloat(targetAmount.replace(',', '.'));
    if (!name.trim() || !target || target <= 0) return;
    onSubmit(goal.id, {
      name: name.trim(),
      target_amount: target,
      icon,
      color,
      monthly_contribution: monthlyContribution
        ? parseFloat(monthlyContribution.replace(',', '.'))
        : null,
      deadline: deadline || null,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-[#f3f4f3] px-5 py-4">
          <h2 className="font-semibold text-[#303333]">Editar objetivo</h2>
          <button onClick={onCancel} className="text-[#9ca3af] hover:text-[#5d605f]">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="max-h-[70vh] overflow-y-auto p-5 space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-[#5d605f]">Nombre *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              required
              className="w-full rounded-xl border border-[#e0e7ef] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-[#5d605f]">
              Importe objetivo (€) *
            </label>
            <input
              type="number"
              value={targetAmount}
              onChange={(e) => setTargetAmount(e.target.value)}
              min="0.01"
              step="0.01"
              required
              className="w-full rounded-xl border border-[#e0e7ef] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-[#5d605f]">
              Aportación mensual (€) — opcional
            </label>
            <input
              type="number"
              value={monthlyContribution}
              onChange={(e) => setMonthlyContribution(e.target.value)}
              min="0.01"
              step="0.01"
              className="w-full rounded-xl border border-[#e0e7ef] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-[#5d605f]">
              Fecha límite — opcional
            </label>
            <input
              type="date"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              className="w-full rounded-xl border border-[#e0e7ef] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
            />
          </div>
          <div>
            <label className="mb-2 block text-xs font-medium text-[#5d605f]">Icono</label>
            <div className="grid grid-cols-10 gap-1">
              {ICONS.map(({ name: n, Icon }) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setIcon(n)}
                  className={`flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
                    icon === n ? 'bg-[#e8f0f8]' : 'hover:bg-[#f3f4f3]'
                  }`}
                >
                  <Icon size={18} style={{ color: icon === n ? color : '#9ca3af' }} />
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-2 block text-xs font-medium text-[#5d605f]">Color</label>
            <div className="flex flex-wrap gap-2">
              {COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className={`h-7 w-7 rounded-full transition-transform ${
                    color === c ? 'scale-125 ring-2 ring-offset-1 ring-[#303333]' : ''
                  }`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>

          {goal.status === 'active' && (
            <div className="rounded-xl border border-green-200 bg-green-50 p-3">
              {confirmComplete ? (
                <div>
                  <p className="text-sm text-green-800">
                    ¿Marcar &quot;{goal.name}&quot; como completado? El objetivo quedará registrado
                    en tu historial.
                  </p>
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      onClick={() => setConfirmComplete(false)}
                      className="flex-1 rounded-lg border border-green-300 py-1.5 text-xs font-medium text-green-700"
                    >
                      Cancelar
                    </button>
                    <button
                      type="button"
                      onClick={() => onMarkCompleted(goal.id)}
                      disabled={isLoading}
                      className="flex-1 rounded-lg bg-green-600 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                    >
                      Confirmar
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirmComplete(true)}
                  className="w-full text-sm font-medium text-green-700 hover:underline"
                >
                  Marcar como completado ✓
                </button>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 rounded-xl border border-[#edeeed] py-2.5 text-sm font-medium text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 rounded-xl bg-[#0060ad] py-2.5 text-sm font-semibold text-white hover:bg-[#0052a3] disabled:opacity-50 transition-colors"
            >
              {isLoading ? 'Guardando...' : 'Guardar cambios'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
