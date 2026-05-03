'use client';

import { useState } from 'react';
import {
  PiggyBank, Wallet, Home, Car, Plane, Heart, Star, Shield,
  GraduationCap, Laptop, Gift, Music, Camera, Book, Coffee,
  Sun, Umbrella, Anchor, Target, Trophy, Plus, Pencil, Trash2,
  type LucideIcon,
} from 'lucide-react';
import { GoalProgressBar } from './GoalProgressBar';
import { ContributionPanel } from './ContributionPanel';
import type { SavingsGoal } from '@/types/goals';

const GOAL_ICONS: Record<string, LucideIcon> = {
  'piggy-bank': PiggyBank, wallet: Wallet, home: Home, car: Car, plane: Plane,
  heart: Heart, star: Star, shield: Shield, 'graduation-cap': GraduationCap,
  laptop: Laptop, gift: Gift, music: Music, camera: Camera, book: Book,
  coffee: Coffee, sun: Sun, umbrella: Umbrella, anchor: Anchor, target: Target,
  trophy: Trophy,
};

const fmt = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });

const PACE_LABELS: Record<string, { label: string; cls: string }> = {
  ahead: { label: 'Adelantado', cls: 'bg-green-100 text-green-700' },
  on_track: { label: 'En ritmo', cls: 'bg-blue-100 text-blue-700' },
  at_risk: { label: 'En riesgo', cls: 'bg-orange-100 text-orange-700' },
};

interface GoalCardProps {
  goal: SavingsGoal;
  onContribute: (id: string, amount: number, note: string | null) => void;
  onEdit: (goal: SavingsGoal) => void;
  onDelete: (goal: SavingsGoal) => void;
  isContributing?: boolean;
}

export function GoalCard({ goal, onContribute, onEdit, onDelete, isContributing }: GoalCardProps) {
  const [showPanel, setShowPanel] = useState(false);
  const Icon = GOAL_ICONS[goal.icon] ?? PiggyBank;
  const pace = goal.pace_status ? PACE_LABELS[goal.pace_status] : null;
  const current = parseFloat(goal.current_amount);
  const target = parseFloat(goal.target_amount);
  const daysLeft = goal.days_remaining;

  let deadlineText: { text: string; cls: string } | null = null;
  if (daysLeft !== null) {
    if (daysLeft < 0) {
      deadlineText = { text: `Vencido hace ${Math.abs(daysLeft)} días`, cls: 'text-red-600' };
    } else if (daysLeft <= 7) {
      deadlineText = { text: `Quedan ${daysLeft} días`, cls: 'text-orange-500' };
    } else {
      deadlineText = { text: `Quedan ${daysLeft} días`, cls: 'text-[#5d605f]' };
    }
  }

  return (
    <div
      className="rounded-2xl bg-white shadow-card overflow-hidden"
      style={{ borderLeft: `4px solid ${goal.color}` }}
    >
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Icon size={20} style={{ color: goal.color }} className="shrink-0" />
            <span className="truncate font-semibold text-[#303333]">{goal.name}</span>
            {pace && (
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${pace.cls}`}>
                {pace.label}
              </span>
            )}
          </div>
          <div className="flex shrink-0 gap-1">
            <button
              onClick={() => onEdit(goal)}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-[#9ca3af] hover:bg-[#f3f4f3] hover:text-[#5d605f] transition-colors"
            >
              <Pencil size={13} />
            </button>
            <button
              onClick={() => onDelete(goal)}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-[#9ca3af] hover:bg-red-50 hover:text-red-500 transition-colors"
            >
              <Trash2 size={13} />
            </button>
          </div>
        </div>

        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs text-[#5d605f]">
              {fmt.format(current)} de {fmt.format(target)}
            </span>
            <span className="text-xs font-semibold" style={{ color: goal.color }}>
              {goal.percentage.toFixed(0)}%
            </span>
          </div>
          <GoalProgressBar percentage={goal.percentage} />
        </div>

        <p className="mt-2 text-xs text-[#9ca3af]">{goal.motivational_message}</p>

        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {deadlineText && (
            <span className={deadlineText.cls}>{deadlineText.text}</span>
          )}
          {goal.estimated_completion_date && (
            <span className="text-[#9ca3af]">
              Estimado:{' '}
              {new Date(goal.estimated_completion_date).toLocaleDateString('es-ES', {
                day: 'numeric', month: 'short', year: 'numeric',
              })}
            </span>
          )}
        </div>

        {goal.status === 'active' && (
          <>
            {showPanel ? (
              <ContributionPanel
                goalId={goal.id}
                onSubmit={(amount, note) => {
                  onContribute(goal.id, amount, note);
                  setShowPanel(false);
                }}
                onCancel={() => setShowPanel(false)}
                isLoading={isContributing}
              />
            ) : (
              <button
                onClick={() => setShowPanel(true)}
                className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-[#cce8d7] py-2 text-sm font-medium text-[#0060ad] hover:border-[#0060ad] hover:bg-[#f0f7ff] transition-colors"
              >
                <Plus size={14} />
                Añadir
              </button>
            )}
          </>
        )}

        {goal.status === 'completed' && (
          <div className="mt-3 flex items-center justify-center gap-1.5 rounded-xl bg-green-50 py-2 text-sm font-medium text-green-700">
            ¡Objetivo cumplido! 🎉
          </div>
        )}
      </div>
    </div>
  );
}
