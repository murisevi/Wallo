'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { goalsApi } from '@/lib/api';
import type { GoalContribution } from '@/types/goals';

const fmtCurrency = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });
const fmtDate = new Intl.DateTimeFormat('es-ES', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
});

interface ContributionHistoryProps {
  goalId: string;
  recentContributions: GoalContribution[];
}

function ContributionRow({ c }: { c: GoalContribution }) {
  const amount = parseFloat(c.amount);
  const isPositive = amount >= 0;
  return (
    <li className="flex items-center gap-2 py-1.5 text-xs">
      <span className="shrink-0 text-[#9ca3af]">{fmtDate.format(new Date(c.created_at))}</span>
      {c.note && <span className="min-w-0 flex-1 truncate text-[#5d605f]">{c.note}</span>}
      {!c.note && <span className="flex-1" />}
      <span className={`shrink-0 font-semibold ${isPositive ? 'text-green-600' : 'text-red-500'}`}>
        {isPositive ? '+' : ''}
        {fmtCurrency.format(amount)}
      </span>
    </li>
  );
}

export function ContributionHistory({ goalId, recentContributions }: ContributionHistoryProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const { data: allContributions, isLoading } = useQuery({
    queryKey: ['goals', goalId, 'contributions'],
    queryFn: () => goalsApi.getContributions(goalId),
    enabled: showAll,
    staleTime: 60_000,
  });

  const contributions = showAll ? (allContributions ?? recentContributions) : recentContributions;
  const mayHaveMore = recentContributions.length >= 5;

  return (
    <div className="mt-3 border-t border-[#f3f4f3] pt-2">
      <button
        onClick={() => setIsOpen((p) => !p)}
        className="flex w-full items-center justify-between text-xs font-medium text-[#0060ad] hover:text-[#0052a3] transition-colors"
      >
        <span>Ver historial</span>
        {isOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {isOpen && (
        <div className="mt-1">
          {contributions.length === 0 ? (
            <p className="py-3 text-center text-xs text-[#9ca3af]">Sin aportaciones todavía</p>
          ) : (
            <ul className="divide-y divide-[#f3f4f3]">
              {contributions.map((c) => (
                <ContributionRow key={c.id} c={c} />
              ))}
            </ul>
          )}

          {showAll && isLoading && (
            <p className="mt-1 text-xs text-[#9ca3af]">Cargando historial completo...</p>
          )}

          {!showAll && mayHaveMore && (
            <button
              onClick={() => setShowAll(true)}
              className="mt-2 text-xs text-[#0060ad] hover:underline"
            >
              Ver todas
            </button>
          )}
        </div>
      )}
    </div>
  );
}
