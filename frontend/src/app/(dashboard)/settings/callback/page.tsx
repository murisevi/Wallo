'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { CheckCircle, Loader2, XCircle } from 'lucide-react';
import Link from 'next/link';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

function CallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const code = searchParams.get('code');

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>(
    code ? 'loading' : 'error',
  );
  const [errorMsg, setErrorMsg] = useState<string | null>(
    code ? null : 'No se recibió el código de autorización del banco.',
  );
  const called = useRef(false);

  useEffect(() => {
    if (!code || called.current) return;
    called.current = true;

    api
      .post('/banking/callback', { code })
      .then(() => {
        queryClient.invalidateQueries({ queryKey: ['connections'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard'] });
        queryClient.invalidateQueries({ queryKey: ['accounts'] });
        setStatus('success');
        setTimeout(() => router.replace('/settings?connected=1'), 1800);
      })
      .catch((err: unknown) => {
        setStatus('error');
        setErrorMsg(
          err instanceof Error ? err.message : 'Error al completar la conexión bancaria.',
        );
      });
  }, [code, router, queryClient]);

  if (status === 'loading') {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <Loader2 size={44} className="animate-spin text-[#8B1A1A]" />
        <p className="text-base font-bold text-[#1a1a1a]">Conectando con tu banco…</p>
        <p className="text-sm text-gray-500">Esto puede tardar unos segundos.</p>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <CheckCircle size={44} className="text-green-600" />
        <p className="text-base font-bold text-[#1a1a1a]">¡Banco conectado correctamente!</p>
        <p className="text-sm text-gray-500">Redirigiendo a Configuración…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4 py-16 text-center">
      <XCircle size={44} className="text-red-400" />
      <div>
        <p className="text-base font-bold text-[#1a1a1a]">No se pudo completar la conexión</p>
        {errorMsg && <p className="mt-1 text-sm text-red-500">{errorMsg}</p>}
      </div>
      <div className="mt-2 flex gap-3">
        <Link
          href="/settings"
          className="rounded-full bg-[#8B1A1A] px-6 py-2.5 text-sm font-bold text-white hover:bg-[#7a1616] transition-colors"
        >
          Volver a Configuración
        </Link>
        <Link
          href="/dashboard"
          className="rounded-full bg-[#F5F5F5] px-6 py-2.5 text-sm font-semibold text-[#1a1a1a] hover:bg-gray-200 transition-colors"
        >
          Ir al panel
        </Link>
      </div>
    </div>
  );
}

export default function SettingsCallbackPage() {
  return (
    <div className="mx-auto max-w-md">
      <div className="overflow-hidden rounded-3xl bg-white shadow-card-lg">
        <Suspense
          fallback={
            <div className="flex flex-col items-center gap-4 py-16">
              <Loader2 size={44} className="animate-spin text-[#8B1A1A]" />
            </div>
          }
        >
          <CallbackContent />
        </Suspense>
      </div>
    </div>
  );
}
