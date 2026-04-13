'use client';

import { Cell, Pie, PieChart, Tooltip } from 'recharts';
import type { CategorySpending } from '@/types/reports';

const fmt = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });

interface SpendingDonutChartProps {
  totalSpending: string;
  categories: CategorySpending[];
  periodLabel: string;
}

export default function SpendingDonutChart({
  totalSpending,
  categories,
  periodLabel,
}: SpendingDonutChartProps) {
  const total = parseFloat(totalSpending);

  const data = categories.map((c) => ({
    name: c.name,
    value: parseFloat(c.amount),
    percentage: c.percentage,
    color: c.color,
  }));

  if (data.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 text-gray-400">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-10 w-10"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p className="text-sm">No hay datos para el período seleccionado</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Donut + center label */}
      <div className="relative">
        <PieChart width={240} height={240}>
          <Pie
            data={data}
            cx={115}
            cy={115}
            innerRadius={72}
            outerRadius={108}
            dataKey="value"
            strokeWidth={2}
            stroke="#fff"
          >
            {data.map((entry, idx) => (
              <Cell key={idx} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => [fmt.format(Number(value)), 'Gasto']}
            contentStyle={{ borderRadius: 8, fontSize: 13 }}
          />
        </PieChart>
        {/* Center label — absolutely positioned over the donut hole */}
        <div
          className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"
        >
          <span className="text-xl font-bold text-gray-900">
            {fmt.format(total)}
          </span>
          <span className="mt-0.5 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
            Total gasto
          </span>
        </div>
      </div>

      {/* Legend grid */}
      <div className="grid w-full grid-cols-2 gap-x-4 gap-y-2">
        {categories.map((c) => (
          <div key={c.name} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
              style={{ backgroundColor: c.color }}
            />
            <span className="truncate text-sm text-gray-600">{c.name}</span>
            <span className="ml-auto text-sm font-semibold text-gray-900">
              {c.percentage}%
            </span>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-400">{periodLabel}</p>
    </div>
  );
}
