'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQueryClient } from '@tanstack/react-query';
import { RefreshCw, PlusCircle } from 'lucide-react';
import { useAuth } from '@/providers/auth-provider';
import { useDashboard } from '@/hooks/useDashboard';
import { BalanceDisplay } from '@/components/features/BalanceDisplay';
import { AccountCard } from '@/components/features/AccountCard';
import { TransactionRow } from '@/components/features/TransactionRow';
import { api } from '@/lib/api';

// ---------------------------------------------------------------------------
// Skeleton primitives
// ---------------------------------------------------------------------------

function SkeletonBalance() {
  return (
    <div className="animate-pulse rounded-2xl bg-amber-100 px-6 py-10 sm:py-14">
      <div className="mx-auto h-3 w-36 rounded-full bg-amber-200" />
      <div className="mx-auto mt-5 h-14 w-64 rounded-xl bg-amber-200" />
      <div className="mx-auto mt-4 h-3 w-40 rounded-full bg-amber-200" />
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex justify-between">
        <div className="h-4 w-28 rounded-full bg-gray-200" />
        <div className="h-5 w-10 rounded-full bg-gray-100" />
      </div>
      <div className="mt-2 h-3 w-20 rounded-full bg-gray-100" />
      <div className="mt-4 h-7 w-32 rounded-lg bg-gray-200" />
    </div>
  );
}

function SkeletonRow() {
  return (
    <div className="flex animate-pulse items-center justify-between gap-4 py-3.5">
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-full bg-gray-100" />
        <div>
          <div className="h-4 w-36 rounded-full bg-gray-200" />
          <div className="mt-1.5 h-3 w-16 rounded-full bg-gray-100" />
        </div>
      </div>
      <div className="h-4 w-20 rounded-full bg-gray-200" />
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

  const accountCount = data?.accounts.length ?? 0;
  const hasAccounts = accountCount > 0;

  async function handleSync() {
    setIsSyncing(true);
    try {
      // Ask the backend to pull fresh balances from Enable Banking
      await api.post<void>('/banking/sync');
    } catch {
      // Sync may partially succeed — still refetch what we have
    } finally {
      setIsSyncing(false);
    }
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['transactions'] });
    refetch();
  }

  // ── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-8">
        <SkeletonBalance />
        <div>
          <div className="mb-3 h-5 w-32 animate-pulse rounded-full bg-gray-200" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        </div>
        <div>
          <div className="mb-3 h-5 w-44 animate-pulse rounded-full bg-gray-200" />
          <div className="rounded-xl border border-gray-200 bg-white px-5 divide-y divide-gray-100">
            {[0, 1, 2, 3, 4].map((i) => (
              <SkeletonRow key={i} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── Error ──────────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="rounded-xl border border-red-100 bg-red-50 px-6 py-10 text-center">
        <p className="text-sm font-medium text-red-700">
          No se pudo cargar el panel. Comprueba tu conexión e inténtalo de nuevo.
        </p>
        <button
          onClick={() => refetch()}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 transition-colors"
        >
          <RefreshCw size={14} />
          Reintentar
        </button>
      </div>
    );
  }

  // ── Content ────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">
            Hola, {user?.name?.split(' ')[0]} 👋
          </h1>
          {data?.last_synced_at && (
            <p className="mt-0.5 text-xs text-gray-400">
              Actualizado{' '}
              {new Date(data.last_synced_at).toLocaleString('es-ES', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </p>
          )}
        </div>
        {hasAccounts && (
          <button
            onClick={handleSync}
            disabled={isSyncing || isFetching}
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-700 disabled:opacity-40 transition-colors"
            title="Actualizar saldos desde el banco"
          >
            <RefreshCw size={13} className={isSyncing || isFetching ? 'animate-spin' : ''} />
            Actualizar
          </button>
        )}
      </div>

      {/* Balance hero */}
      <BalanceDisplay
        amount={data?.total_balance ?? '0'}
        currency={user?.currency ?? 'EUR'}
        accountCount={accountCount}
      />

      {/* ── No accounts — empty state ─────────────────────────────────── */}
      {!hasAccounts ? (
        <div className="rounded-xl border-2 border-dashed border-gray-200 bg-white px-6 py-14 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-50">
            <PlusCircle className="text-amber-500" size={28} />
          </div>
          <h2 className="mt-4 text-base font-semibold text-gray-800">
            Conecta tu banco para empezar
          </h2>
          <p className="mt-2 text-sm text-gray-500">
            Vincula tus cuentas con Open Banking y tendrás una visión completa de tus finanzas en
            segundos.
          </p>
          <Link
            href="/banking/connect"
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-amber-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-amber-500 transition-colors"
          >
            <PlusCircle size={16} />
            Conectar banco
          </Link>
        </div>
      ) : (
        <>
          {/* ── Account grid ──────────────────────────────────────────── */}
          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
                Cuentas conectadas
              </h2>
              <Link
                href="/banking/connect"
                className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 hover:text-amber-500"
              >
                <PlusCircle size={12} />
                Añadir
              </Link>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data?.accounts.map((account) => (
                <AccountCard key={account.id} account={account} />
              ))}
            </div>
          </section>

          {/* ── Recent transactions ───────────────────────────────────── */}
          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
                Últimas transacciones
              </h2>
              <Link
                href="/transactions"
                className="text-xs font-medium text-amber-600 hover:text-amber-500"
              >
                Ver todas →
              </Link>
            </div>

            {(data?.recent_transactions.length ?? 0) === 0 ? (
              <div className="rounded-xl border border-gray-200 bg-white px-5 py-8 text-center">
                <p className="text-sm text-gray-400">
                  No hay transacciones recientes. Puede tardar unos segundos en sincronizar.
                </p>
              </div>
            ) : (
              <div className="rounded-xl border border-gray-200 bg-white px-5 divide-y divide-gray-100">
                {data?.recent_transactions.map((txn) => (
                  <TransactionRow key={txn.id} transaction={txn} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
