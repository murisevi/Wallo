'use client';

import { useEffect } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface DashboardErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function DashboardError({ error, reset }: DashboardErrorProps) {
  useEffect(() => {
    console.error('[Dashboard error]', error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-3xl bg-white px-8 py-12 text-center shadow-[0_20px_40px_rgba(48,51,51,0.08)]">
        <AlertCircle className="mx-auto text-red-400" size={36} />
        <h2 className="mt-4 text-base font-bold text-[#303333]">Algo salió mal</h2>
        <p className="mt-2 text-sm text-[#5d605f]">
          {error.message || 'Se produjo un error inesperado. Por favor inténtalo de nuevo.'}
        </p>
        <button
          onClick={reset}
          className="mt-6 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-amber-500 to-amber-600 px-5 py-2.5 text-sm font-bold text-white hover:from-amber-400 hover:to-amber-500 transition-all"
        >
          <RefreshCw size={14} />
          Reintentar
        </button>
      </div>
    </div>
  );
}
