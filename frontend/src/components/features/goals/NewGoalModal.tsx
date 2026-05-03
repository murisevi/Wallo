'use client';

import { useState } from 'react';
import {
  PiggyBank, Wallet, Home, Car, Plane, Heart, Star, Shield,
  GraduationCap, Laptop, Gift, Music, Camera, Book, Coffee,
  Sun, Umbrella, Anchor, Target, Trophy, PlusCircle, X,
  type LucideIcon,
} from 'lucide-react';
import type { GoalCreate } from '@/types/goals';

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

const PRESETS = [
  { name: 'Fondo de emergencia', icon: 'shield', color: '#EF4444' },
  { name: 'Vacaciones', icon: 'plane', color: '#F59E0B' },
  { name: 'Entrada de piso', icon: 'home', color: '#8B5CF6' },
  { name: 'Coche nuevo', icon: 'car', color: '#3B82F6' },
  { name: 'Tecnología', icon: 'laptop', color: '#6366F1' },
  { name: 'Educación', icon: 'graduation-cap', color: '#10B981' },
  { name: 'Boda', icon: 'heart', color: '#EC4899' },
  { name: 'Otro...', icon: 'plus-circle', color: '#6B7280' },
];

interface NewGoalModalProps {
  onSubmit: (data: GoalCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function NewGoalModal({ onSubmit, onCancel, isLoading }: NewGoalModalProps) {
  const [step, setStep] = useState<'preset' | 'form'>('preset');
  const [name, setName] = useState('');
  const [targetAmount, setTargetAmount] = useState('');
  const [monthlyContribution, setMonthlyContribution] = useState('');
  const [deadline, setDeadline] = useState('');
  const [icon, setIcon] = useState('piggy-bank');
  const [color, setColor] = useState('#3B82F6');

  function handlePreset(preset: (typeof PRESETS)[0]) {
    if (preset.name !== 'Otro...') {
      setName(preset.name);
      setIcon(preset.icon);
      setColor(preset.color);
    }
    setStep('form');
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const target = parseFloat(targetAmount.replace(',', '.'));
    if (!name.trim() || !target || target <= 0) return;
    onSubmit({
      name: name.trim(),
      target_amount: target,
      icon,
      color,
      monthly_contribution: monthlyContribution
        ? parseFloat(monthlyContribution.replace(',', '.'))
        : null,
      deadline: deadline || null,
      priority: 0,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-[#f3f4f3] px-5 py-4">
          <h2 className="font-semibold text-[#303333]">
            {step === 'preset' ? 'Nuevo objetivo' : 'Configurar objetivo'}
          </h2>
          <button onClick={onCancel} className="text-[#9ca3af] hover:text-[#5d605f]">
            <X size={20} />
          </button>
        </div>

        {step === 'preset' ? (
          <div className="p-5">
            <p className="mb-4 text-sm text-[#5d605f]">¿Para qué quieres ahorrar?</p>
            <div className="grid grid-cols-4 gap-2">
              {PRESETS.map((preset) => {
                const found = ICONS.find((i) => i.name === preset.icon);
                const Icon = found ? found.Icon : PlusCircle;
                return (
                  <button
                    key={preset.name}
                    onClick={() => handlePreset(preset)}
                    className="flex flex-col items-center gap-1.5 rounded-xl p-3 hover:bg-[#f3f4f3] transition-colors"
                  >
                    <Icon size={24} style={{ color: preset.color }} />
                    <span className="text-center text-xs text-[#5d605f] leading-tight">
                      {preset.name}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="max-h-[70vh] overflow-y-auto p-5 space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-[#5d605f]">
                Nombre del objetivo *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={100}
                required
                placeholder="Ej: Vacaciones en Japón"
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
                placeholder="Ej: 2000"
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
                placeholder="Ej: 100 €/mes"
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
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setStep('preset')}
                className="flex-1 rounded-xl border border-[#edeeed] py-2.5 text-sm font-medium text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
              >
                Atrás
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 rounded-xl bg-[#0060ad] py-2.5 text-sm font-semibold text-white hover:bg-[#0052a3] disabled:opacity-50 transition-colors"
              >
                {isLoading ? 'Creando...' : 'Crear objetivo'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
