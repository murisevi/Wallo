'use client';

import type { ViewPeriod } from '@/types/reports';

interface Option {
  value: ViewPeriod;
  label: string;
}

const OPTIONS: Option[] = [
  { value: 'month', label: 'Mes' },
  { value: 'quarter', label: 'Trimestre' },
  { value: 'year', label: 'Año' },
];

interface PeriodSelectorProps {
  value: ViewPeriod;
  onChange: (period: ViewPeriod) => void;
}

export default function PeriodSelector({ value, onChange }: PeriodSelectorProps) {
  const activeValue = value;
  return (
    <div className="flex items-center gap-1 rounded-full bg-gray-100 p-1">
      {OPTIONS.map((opt) => {
        const isActive = opt.value === activeValue;
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-all ${
              isActive
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
