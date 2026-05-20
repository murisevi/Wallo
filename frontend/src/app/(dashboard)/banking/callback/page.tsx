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
        setStatus('success');
        // Check if the connect flow was initiated from a specific page (e.g. /settings)
        const returnTo = sessionStorage.getItem('wallo:banking_return_to') ?? '/dashboard';
        sessionStorage.removeItem('wallo:banking_return_to');
        const destination = returnTo === '/settings' ? '/settings?connected=1' : returnTo;
        setTimeout(() => router.replace(destination), 1800);
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
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <Loader2 size={44} className="animate-spin text-amber-500" />
        <p className="text-base font-bold text-[#303333]">Conectando con tu banco…</p>
        <p className="text-sm text-[#5d605f]">Esto puede tardar unos segundos.</p>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <CheckCircle size={44} className="text-[#166534]" />
        <p className="text-base font-bold text-[#303333]">¡Banco conectado correctamente!</p>
        <p className="text-sm text-[#5d605f]">Redirigiendo al panel…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4 py-16 text-center">
      <XCircle size={44} className="text-red-400" />
      <div>
        <p className="text-base font-bold text-[#303333]">No se pudo completar la conexión</p>
        {errorMsg && <p className="mt-1 text-sm text-red-500">{errorMsg}</p>}
      </div>
      <div className="mt-2 flex gap-3">
        <Link
          href="/banking/connect"
          className="rounded-full bg-gradient-to-r from-amber-500 to-amber-600 px-6 py-2.5 text-sm font-bold text-white hover:from-amber-400 hover:to-amber-500 transition-all"
        >
          Reintentar
        </Link>
        <Link
          href="/dashboard"
          className="rounded-full bg-[#f3f4f3] px-6 py-2.5 text-sm font-semibold text-[#303333] hover:bg-[#edeeed] transition-colors"
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
      <div className="overflow-hidden rounded-3xl bg-white shadow-card-lg">
        <Suspense
          fallback={
            <div className="flex flex-col items-center gap-4 py-16">
              <Loader2 size={44} className="animate-spin text-amber-500" />
            </div>
          }
        >
          <CallbackContent />
        </Suspense>
      </div>
    </div>
  );
}
