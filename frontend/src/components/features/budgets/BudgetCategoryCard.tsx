'use client';

import Link from 'next/link';
import {
  ShoppingCart, Utensils, Car, Home, Heart, Shirt, BookOpen, Repeat, HelpCircle,
} from 'lucide-react';
import type { Budget } from '@/types/budget';

// ─── Helpers ─────────────────────────────────────────────────────────────────

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

function formatEur(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(num);
}

function progressBarColor(pct: number): string {
  if (pct >= 100) return 'bg-red-500';
  if (pct >= 80) return 'bg-yellow-500';
  return 'bg-green-500';
}

/** Returns YYYY-MM-DD for the last day of the given month (1-indexed). */
function lastDayOfMonth(year: number, month: number): string {
  // Use UTC to avoid timezone offset shifting the date to the previous day.
  const d = new Date(Date.UTC(year, month, 0)); // day 0 of next month = last day of this month
  return d.toISOString().slice(0, 10);
}

// ─── Component ───────────────────────────────────────────────────────────────

interface BudgetCategoryCardProps {
  budget: Budget;
}

export function BudgetCategoryCard({ budget }: BudgetCategoryCardProps) {
  const pct = Math.min(budget.percentage, 100);
  const colors = CATEGORY_COLORS[budget.category_icon] ?? { bg: 'bg-gray-100', icon: 'text-gray-500' };
  const Icon = ICON_MAP[budget.category_icon] ?? HelpCircle;

  const dateFrom = `${budget.year}-${String(budget.month).padStart(2, '0')}-01`;
  const dateTo = lastDayOfMonth(budget.year, budget.month);

  const href = `/transactions?${new URLSearchParams({
    category_id: budget.category_id,
    date_from: dateFrom,
    date_to: dateTo,
  }).toString()}`;

  return (
    <Link
      href={href}
      className="block cursor-pointer rounded-2xl bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
    >
      {/* Top row: icon + name + amounts */}
      <div className="flex items-center gap-3">
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${colors.bg}`}
        >
          <Icon size={18} className={colors.icon} />
        </div>

        <p className="flex-1 text-sm font-bold text-[#303333]">{budget.category_name}</p>

        <p className="shrink-0 text-xs text-[#5d605f]">
          Gastado{' '}
          <span className="font-semibold text-[#303333]">{formatEur(budget.amount_spent)}</span>
          {' / '}
          {formatEur(budget.amount_limit)}
        </p>
      </div>

      {/* Progress bar */}
      <div className="mt-3 flex items-center gap-3">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
          <div
            className={`h-full rounded-full transition-all ${progressBarColor(budget.percentage)}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="w-10 shrink-0 text-right text-xs font-semibold text-[#5d605f]">
          {budget.percentage.toFixed(0)}%
        </span>
      </div>
    </Link>
  );
}
