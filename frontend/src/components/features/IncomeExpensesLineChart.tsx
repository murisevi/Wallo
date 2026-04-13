'use client';

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { TimeDataPoint } from '@/types/reports';

const fmt = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });

interface IncomeExpensesLineChartProps {
  dataPoints: TimeDataPoint[];
}

const INCOME_COLOR = '#1A5632';
const EXPENSE_COLOR = '#2471A3';

export default function IncomeExpensesLineChart({ dataPoints }: IncomeExpensesLineChartProps) {
  const data = dataPoints.map((p) => ({
    label: p.label,
    Ingresos: parseFloat(p.income),
    Gastos: parseFloat(p.expenses),
  }));

  if (data.length === 0 || data.every((d) => d.Ingresos === 0 && d.Gastos === 0)) {
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
            d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"
          />
        </svg>
        <p className="text-sm">No hay datos para el período seleccionado</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <CartesianGrid strokeDasharray="4 4" stroke="#f0f0f0" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: '#9CA3AF', fontWeight: 600 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          hide
          tickFormatter={(v: number) => fmt.format(v)}
        />
        <Tooltip
          formatter={(value, name) => [fmt.format(Number(value)), name as string]}
          contentStyle={{ borderRadius: 8, fontSize: 13 }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
          formatter={(value: string) => (
            <span style={{ color: value === 'Ingresos' ? INCOME_COLOR : EXPENSE_COLOR }}>
              {value}
            </span>
          )}
        />
        <Line
          type="monotone"
          dataKey="Ingresos"
          stroke={INCOME_COLOR}
          strokeWidth={3}
          dot={{ r: 4, fill: INCOME_COLOR }}
          activeDot={{ r: 6 }}
        />
        <Line
          type="monotone"
          dataKey="Gastos"
          stroke={EXPENSE_COLOR}
          strokeWidth={3}
          dot={{ r: 4, fill: EXPENSE_COLOR }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
