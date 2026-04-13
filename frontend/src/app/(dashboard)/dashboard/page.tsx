'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQueryClient } from '@tanstack/react-query';
import { RefreshCw, PlusCircle, Calendar, TrendingDown } from 'lucide-react';
import { useAuth } from '@/providers/auth-provider';
import { useDashboard } from '@/hooks/useDashboard';
import { TransactionRow } from '@/components/features/TransactionRow';
import { api } from '@/lib/api';

// ---------------------------------------------------------------------------
// Skeletons
// ---------------------------------------------------------------------------

function SkeletonHero() {
  return (
    <div className="animate-pulse rounded-3xl bg-[#e8f5ee] px-8 py-12 text-center">
      <div className="mx-auto h-3 w-40 rounded-full bg-[#cce8d7]" />
      <div className="mx-auto mt-5 h-16 w-72 rounded-2xl bg-[#cce8d7]" />
      <div className="mx-auto mt-4 h-3 w-48 rounded-full bg-[#cce8d7]" />
    </div>
  );
}

function SkeletonRow() {
  return (
    <div className="flex animate-pulse items-center justify-between gap-4 py-4">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-full bg-[#f3f4f3]" />
        <div>
          <div className="h-4 w-36 rounded-full bg-[#f3f4f3]" />
          <div className="mt-1.5 h-3 w-16 rounded-full bg-[#edeeed]" />
        </div>
      </div>
      <div className="h-4 w-20 rounded-full bg-[#f3f4f3]" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading, isError, refetch, isFetching } = useDashboard();
  const queryClient = useQueryClient();
  const [isSyncing, setIsSyncing] = useState(false);

  const firstName = user?.name?.split(' ')[0] ?? '';
  const accountCount = data?.accounts.length ?? 0;
  const hasAccounts = accountCount > 0;

  const totalBalance =
    data?.total_balance != null
      ? new Intl.NumberFormat('es-ES', {
          style: 'currency',
          currency: user?.currency ?? 'EUR',
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(parseFloat(data.total_balance))
      : '—';

  async function handleSync() {
    setIsSyncing(true);
    try {
      await api.post<void>('/banking/sync');
    } catch {
      // Sync may partially succeed — still refetch
    } finally {
      setIsSyncing(false);
    }
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['transactions'] });
    refetch();
  }

  // ── Loading ──────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-8">
        <div>
          <div className="h-8 w-48 animate-pulse rounded-full bg-[#f3f4f3]" />
          <div className="mt-2 h-4 w-64 animate-pulse rounded-full bg-[#edeeed]" />
        </div>
        <SkeletonHero />
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl bg-white p-6 shadow-[0_4px_16px_rgba(48,51,51,0.06)]">
            <div className="mb-4 h-5 w-40 animate-pulse rounded-full bg-[#f3f4f3]" />
            {[0, 1, 2, 3, 4].map((i) => <SkeletonRow key={i} />)}
          </div>
          <div className="rounded-2xl bg-white p-6 shadow-[0_4px_16px_rgba(48,51,51,0.06)]">
            <div className="mb-4 h-5 w-36 animate-pulse rounded-full bg-[#f3f4f3]" />
            <div className="h-24 w-full animate-pulse rounded-xl bg-[#f3f4f3]" />
          </div>
        </div>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="rounded-2xl bg-white px-8 py-12 text-center shadow-[0_4px_16px_rgba(48,51,51,0.06)]">
        <p className="text-sm font-medium text-red-600">
          No se pudo cargar el panel. Comprueba tu conexión e inténtalo de nuevo.
        </p>
        <button
          onClick={() => refetch()}
          className="mt-4 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] px-5 py-2.5 text-sm font-bold text-white hover:opacity-90 transition-all"
        >
          <RefreshCw size={14} />
          Reintentar
        </button>
      </div>
    );
  }

  // ── Content ──────────────────────────────────────────────────────────────
  return (
    <div className="space-y-8">
      {/* Greeting */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-[#303333]">
            Hola, {firstName}
          </h1>
          <p className="mt-1 text-sm text-[#5d605f]">Que tengas un día tranquilo y bajo control.</p>
        </div>
        {hasAccounts && (
          <button
            onClick={handleSync}
            disabled={isSyncing || isFetching}
            title="Actualizar saldos desde el banco"
            className="mt-1 flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium text-[#5d605f] hover:bg-[#f3f4f3] hover:text-[#303333] disabled:opacity-40 transition-colors"
          >
            <RefreshCw size={13} className={isSyncing || isFetching ? 'animate-spin' : ''} />
            Actualizar
          </button>
        )}
      </div>

      {/* Hero balance card — soft mint green */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#e8f5ee] via-[#ddf0e5] to-[#cce8d7] px-8 py-12 text-center shadow-[0_4px_24px_rgba(48,51,51,0.08)]">
        {/* Decorative rings */}
        <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-white/30" />
        <div className="pointer-events-none absolute -bottom-20 -left-20 h-72 w-72 rounded-full bg-white/20" />

        <p className="relative text-xs font-bold uppercase tracking-[0.22em] text-[#5d605f]">
          Dinero libre disponible
        </p>
        <p className="relative mt-4 text-6xl font-extrabold tabular-nums tracking-tight text-[#1a3a2a] lg:text-7xl">
          {totalBalance}
        </p>
        <div className="relative mt-5 inline-flex items-center gap-1.5 rounded-full bg-white/60 px-4 py-1.5 backdrop-blur-sm">
          <TrendingDown size={13} className="text-[#216c36]" />
          <p className="text-xs font-medium text-[#5d605f]">
            {accountCount === 0
              ? 'Conecta tu banco para ver tus saldos'
              : accountCount === 1
                ? 'En 1 cuenta conectada'
                : `En ${accountCount} cuentas conectadas`}
          </p>
        </div>
      </div>

      {/* No accounts — empty state */}
      {!hasAccounts && (
        <div className="rounded-2xl bg-white px-8 py-14 text-center shadow-[0_4px_16px_rgba(48,51,51,0.06)]">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#e8f0f8]">
            <PlusCircle className="text-[#0060ad]" size={28} />
          </div>
          <h2 className="mt-5 text-base font-bold text-[#303333]">
            Conecta tu banco para empezar
          </h2>
          <p className="mt-2 text-sm text-[#5d605f]">
            Vincula tus cuentas con Open Banking y tendrás una visión completa de tus finanzas en segundos.
          </p>
          <Link
            href="/banking/connect"
            className="mt-6 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] px-6 py-3 text-sm font-bold text-white shadow-sm hover:opacity-90 transition-all"
          >
            <PlusCircle size={16} />
            Conectar banco
          </Link>
        </div>
      )}

      {/* Two-column: recent transactions + próximos cobros */}
      {hasAccounts && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Últimos movimientos */}
          <div className="rounded-2xl bg-white p-6 shadow-[0_4px_16px_rgba(48,51,51,0.06)]">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-base font-bold text-[#303333]">Últimos movimientos</h2>
              <Link
                href="/transactions"
                className="text-xs font-semibold text-[#0060ad] hover:text-[#68abff] transition-colors"
              >
                Ver todo
              </Link>
            </div>

            {(data?.recent_transactions.length ?? 0) === 0 ? (
              <p className="py-8 text-center text-sm text-[#5d605f]">
                No hay transacciones recientes. Puede tardar unos segundos en sincronizar.
              </p>
            ) : (
              <div className="space-y-1">
                {data?.recent_transactions.map((txn) => (
                  <TransactionRow key={txn.id} transaction={txn} />
                ))}
              </div>
            )}
          </div>

          {/* Próximos cobros */}
          <div className="rounded-2xl bg-white p-6 shadow-[0_4px_16px_rgba(48,51,51,0.06)]">
            <h2 className="mb-5 text-base font-bold text-[#303333]">Próximos cobros</h2>
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#f3f4f3]">
                <Calendar size={22} className="text-[#5d605f]" />
              </div>
              <p className="mt-3 text-sm text-[#5d605f]">No hay cobros próximos detectados.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
