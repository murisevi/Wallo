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
      <div className="w-full max-w-sm rounded-2xl border border-red-100 bg-red-50 px-8 py-12 text-center">
        <AlertCircle className="mx-auto text-red-400" size={36} />
        <h2 className="mt-4 text-base font-semibold text-red-700">Algo salió mal</h2>
        <p className="mt-2 text-sm text-gray-500">
          {error.message || 'Se produjo un error inesperado. Por favor inténtalo de nuevo.'}
        </p>
        <button
          onClick={reset}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-red-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-500 transition-colors"
        >
          <RefreshCw size={14} />
          Reintentar
        </button>
      </div>
    </div>
  );
}
