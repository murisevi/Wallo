'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { CheckCircle, Loader2, XCircle } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';

// useSearchParams must be inside a Suspense boundary in Next.js 14.
function CallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const code = searchParams.get('code');

  // Derive initial status from code presence — no setState in the effect.
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>(
    code ? 'loading' : 'error',
  );
  const [errorMsg, setErrorMsg] = useState<string | null>(
    code ? null : 'No se recibió el código de autorización del banco.',
  );
  // Prevent double-invocation in React Strict Mode.
  const called = useRef(false);

  useEffect(() => {
    if (!code || called.current) return;
    called.current = true;

    api
      .post('/banking/callback', { code })
      .then(() => {
        setStatus('success');
        setTimeout(() => router.replace('/dashboard'), 1800);
      })
      .catch((err: unknown) => {
        setStatus('error');
        setErrorMsg(
          err instanceof Error ? err.message : 'Error al completar la conexión bancaria.',
        );
      });
  }, [code, router]);

  if (status === 'loading') {
    return (
      <div className="flex flex-col items-center gap-4 py-20 text-center">
        <Loader2 size={44} className="animate-spin text-amber-400" />
        <p className="text-sm font-medium text-gray-700">Conectando con tu banco…</p>
        <p className="text-xs text-gray-400">Esto puede tardar unos segundos.</p>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="flex flex-col items-center gap-4 py-20 text-center">
        <CheckCircle size={44} className="text-green-500" />
        <p className="text-sm font-medium text-gray-700">¡Banco conectado correctamente!</p>
        <p className="text-xs text-gray-400">Redirigiendo al panel…</p>
      </div>
    );
  }

  // error
  return (
    <div className="flex flex-col items-center gap-4 py-20 text-center">
      <XCircle size={44} className="text-red-400" />
      <div>
        <p className="text-sm font-medium text-gray-700">No se pudo completar la conexión</p>
        {errorMsg && <p className="mt-1 text-xs text-red-500">{errorMsg}</p>}
      </div>
      <div className="flex gap-3">
        <Link
          href="/banking/connect"
          className="rounded-xl bg-amber-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-amber-500 transition-colors"
        >
          Reintentar
        </Link>
        <Link
          href="/dashboard"
          className="rounded-xl border border-gray-200 px-5 py-2.5 text-sm font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Ir al panel
        </Link>
      </div>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <div className="mx-auto max-w-md">
      <Suspense
        fallback={
          <div className="flex flex-col items-center gap-4 py-20">
            <Loader2 size={44} className="animate-spin text-amber-400" />
          </div>
        }
      >
        <CallbackContent />
      </Suspense>
    </div>
  );
}
