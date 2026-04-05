'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ChevronLeft, ChevronRight, RefreshCw, Search } from 'lucide-react';
import { useTransactions } from '@/hooks/useTransactions';
import { TransactionRow } from '@/components/features/TransactionRow';

const PAGE_SIZE = 20;

function SkeletonRow() {
  return (
    <div className="flex animate-pulse items-center justify-between gap-4 py-3.5">
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-full bg-gray-100" />
        <div>
          <div className="h-4 w-40 rounded-full bg-gray-200" />
          <div className="mt-1.5 h-3 w-20 rounded-full bg-gray-100" />
        </div>
      </div>
      <div className="h-4 w-20 rounded-full bg-gray-200" />
    </div>
  );
}

export default function TransactionsPage() {
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');

  const { data, isLoading, isError, refetch } = useTransactions({
    page,
    pageSize: PAGE_SIZE,
    search: search || undefined,
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearch(searchInput.trim());
    setPage(1);
  }

  function handleClearSearch() {
    setSearchInput('');
    setSearch('');
    setPage(1);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          href="/dashboard"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
        >
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Transacciones</h1>
          {data && (
            <p className="text-sm text-gray-400">
              {data.total} {data.total === 1 ? 'movimiento' : 'movimientos'}
            </p>
          )}
        </div>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search
            size={15}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="Buscar descripción, titular…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full rounded-xl border border-gray-200 bg-white py-2.5 pl-9 pr-4 text-sm outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-shadow"
          />
        </div>
        <button
          type="submit"
          className="rounded-xl bg-amber-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-amber-500 transition-colors"
        >
          Buscar
        </button>
        {search && (
          <button
            type="button"
            onClick={handleClearSearch}
            className="rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Limpiar
          </button>
        )}
      </form>

      {/* Error state */}
      {isError && (
        <div className="rounded-xl border border-red-100 bg-red-50 px-5 py-6 text-center">
          <p className="text-sm font-medium text-red-700">
            No se pudieron cargar las transacciones.
          </p>
          <button
            onClick={() => refetch()}
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 transition-colors"
          >
            <RefreshCw size={13} />
            Reintentar
          </button>
        </div>
      )}

      {/* Transaction list */}
      {!isError && (
        <div className="rounded-xl border border-gray-200 bg-white px-5 divide-y divide-gray-100">
          {isLoading ? (
            Array.from({ length: PAGE_SIZE }, (_, i) => <SkeletonRow key={i} />)
          ) : (data?.transactions.length ?? 0) === 0 ? (
            <div className="py-14 text-center">
              <p className="text-sm text-gray-400">
                {search ? 'No se encontraron transacciones.' : 'Aún no hay transacciones.'}
              </p>
            </div>
          ) : (
            data?.transactions.map((txn) => <TransactionRow key={txn.id} transaction={txn} />)
          )}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-400">
            Página {page} de {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="inline-flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
            >
              <ChevronLeft size={14} />
              Anterior
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="inline-flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
            >
              Siguiente
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
