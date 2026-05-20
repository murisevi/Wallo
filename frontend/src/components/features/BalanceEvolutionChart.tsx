'use client';

import { useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { BalanceEvolutionResponse } from '@/types/reports';

const fmtEur = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });

interface BalanceEvolutionChartProps {
  data: BalanceEvolutionResponse;
}

type DisplayMode = 'eur' | 'pct';

export default function BalanceEvolutionChart({ data }: BalanceEvolutionChartProps) {
  const [mode, setDisplayMode] = useState<DisplayMode>('eur');

  const isPositive = parseFloat(data.total_change) >= 0;
  const areaColor = isPositive ? '#1A5632' : '#C0392B';
  const gradientId = isPositive ? 'balanceGradientGreen' : 'balanceGradientRed';

  const startBalance = parseFloat(data.start_balance);

  const chartData = data.data_points.map((pt) => {
    const balance = parseFloat(pt.balance);
    const cumulativePct =
      startBalance !== 0 ? ((balance - startBalance) / Math.abs(startBalance)) * 100 : 0;
    return {
      label: pt.label,
      balance,
      cumulativePct: parseFloat(cumulativePct.toFixed(2)),
    };
  });

  const totalChange = parseFloat(data.total_change);
  const totalChangePct = data.total_change_percent;

  if (chartData.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-gray-400">
        No hay datos para el período seleccionado
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* ── Summary row ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <SummaryTile
          label="Patrimonio inicial"
          value={fmtEur.format(parseFloat(data.start_balance))}
        />
        <SummaryTile
          label="Patrimonio final"
          value={fmtEur.format(parseFloat(data.end_balance))}
        />
        <SummaryTile
          label="Variación"
          value={`${totalChange >= 0 ? '+' : ''}${fmtEur.format(totalChange)}`}
          positive={totalChange >= 0}
        />
        <SummaryTile
          label="Variación %"
          value={`${totalChangePct >= 0 ? '+' : ''}${totalChangePct.toFixed(2)}%`}
          positive={totalChangePct >= 0}
        />
      </div>

      {/* ── Toggle ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-end">
        <div className="flex overflow-hidden rounded-lg border border-gray-200 text-xs font-medium">
          <button
            onClick={() => setDisplayMode('eur')}
            className={`px-3 py-1.5 transition-colors ${
              mode === 'eur'
                ? 'bg-gray-900 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            €
          </button>
          <button
            onClick={() => setDisplayMode('pct')}
            className={`px-3 py-1.5 transition-colors ${
              mode === 'pct'
                ? 'bg-gray-900 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            %
          </button>
        </div>
      </div>

      {/* ── Area chart ──────────────────────────────────────────────────── */}
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={areaColor} stopOpacity={0.25} />
              <stop offset="95%" stopColor={areaColor} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            axisLine={false}
            tickLine={false}
            width={mode === 'eur' ? 72 : 48}
            tickFormatter={(v: number) =>
              mode === 'eur' ? fmtEur.format(v) : `${v.toFixed(1)}%`
            }
          />
          <Tooltip
            contentStyle={{ borderRadius: 8, fontSize: 13 }}
            formatter={(value) =>
              mode === 'eur'
                ? [fmtEur.format(Number(value)), 'Patrimonio']
                : [`${Number(value).toFixed(2)}%`, 'Variación acum.']
            }
          />
          <Area
            type="monotone"
            dataKey={mode === 'eur' ? 'balance' : 'cumulativePct'}
            stroke={areaColor}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-component
// ---------------------------------------------------------------------------

function SummaryTile({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive?: boolean;
}) {
  const color =
    positive === undefined
      ? 'text-gray-900'
      : positive
        ? 'text-green-700'
        : 'text-red-600';
  return (
    <div className="rounded-lg bg-gray-50 px-3 py-2">
      <p className="text-[11px] font-medium uppercase tracking-wide text-gray-400">{label}</p>
      <p className={`mt-0.5 text-sm font-bold ${color}`}>{value}</p>
    </div>
  );
}
