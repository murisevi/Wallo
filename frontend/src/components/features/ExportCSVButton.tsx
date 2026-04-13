'use client';

import { Download } from 'lucide-react';
import { useExportCSV } from '@/hooks/useReports';
import type { PeriodEnum } from '@/types/reports';

interface ExportCSVButtonProps {
  period: PeriodEnum;
  date?: string;
}

export default function ExportCSVButton({ period, date }: ExportCSVButtonProps) {
  const { mutate, isPending } = useExportCSV();

  return (
    <button
      onClick={() => mutate({ period, date })}
      disabled={isPending}
      className="flex items-center gap-2 rounded-full bg-[#1B4F72] px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:opacity-60"
    >
      <Download size={16} />
      {isPending ? 'Exportando…' : 'Exportar CSV'}
    </button>
  );
}
