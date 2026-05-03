'use client';

import { useState } from 'react';
import { X } from 'lucide-react';

interface ContributionPanelProps {
  goalId: string;
  onSubmit: (amount: number, note: string | null) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const QUICK_AMOUNTS = [10, 50, 100, 500];

export function ContributionPanel({
  onSubmit,
  onCancel,
  isLoading,
}: ContributionPanelProps) {
  const [isWithdraw, setIsWithdraw] = useState(false);
  const [customAmount, setCustomAmount] = useState('');
  const [note, setNote] = useState('');

  function handleQuick(amount: number) {
    const final = isWithdraw ? -amount : amount;
    onSubmit(final, note.trim() || null);
  }

  function handleCustomSubmit() {
    const val = parseFloat(customAmount.replace(',', '.'));
    if (!val || val <= 0) return;
    const final = isWithdraw ? -val : val;
    onSubmit(final, note.trim() || null);
  }

  return (
    <div
      className={`mt-3 rounded-xl border-2 p-4 ${isWithdraw ? 'border-orange-300 bg-orange-50' : 'border-[#e8f0f8] bg-[#f8fafc]'}`}
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[#303333]">
            {isWithdraw ? 'Retirar fondos' : 'Añadir fondos'}
          </span>
          <button
            onClick={() => setIsWithdraw((p) => !p)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              isWithdraw
                ? 'bg-orange-100 text-orange-700'
                : 'bg-[#e8f0f8] text-[#0060ad]'
            }`}
          >
            {isWithdraw ? 'Modo retirar' : 'Modo añadir'}
          </button>
        </div>
        <button onClick={onCancel} className="text-[#9ca3af] hover:text-[#5d605f]">
          <X size={16} />
        </button>
      </div>

      <div className="mb-3 flex gap-2">
        {QUICK_AMOUNTS.map((amt) => (
          <button
            key={amt}
            onClick={() => handleQuick(amt)}
            disabled={isLoading}
            className={`flex-1 rounded-lg py-2 text-sm font-semibold transition-colors disabled:opacity-50 ${
              isWithdraw
                ? 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                : 'bg-[#e8f0f8] text-[#0060ad] hover:bg-[#d0e4f5]'
            }`}
          >
            {isWithdraw ? '-' : '+'}{amt}€
          </button>
        ))}
      </div>

      <div className="mb-2 flex gap-2">
        <input
          type="number"
          min="0"
          step="0.01"
          value={customAmount}
          onChange={(e) => setCustomAmount(e.target.value)}
          placeholder="Cantidad personalizada"
          className={`flex-1 rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 ${
            isWithdraw
              ? 'border-orange-300 focus:ring-orange-200'
              : 'border-[#e0e7ef] focus:ring-[#3B82F6]/20'
          }`}
        />
        <button
          onClick={handleCustomSubmit}
          disabled={isLoading || !customAmount}
          className="rounded-lg bg-[#0060ad] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0052a3] disabled:opacity-50 transition-colors"
        >
          {isLoading ? '...' : isWithdraw ? 'Retirar' : 'Añadir'}
        </button>
      </div>

      <input
        type="text"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Nota opcional..."
        maxLength={200}
        className="w-full rounded-lg border border-[#e0e7ef] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
      />
    </div>
  );
}
