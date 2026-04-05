'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Building2, Loader2, ArrowLeft } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { api } from '@/lib/api';
import type { BankInstitution } from '@/types';

export default function ConnectBankPage() {
  const [search, setSearch] = useState('');
  const [connecting, setConnecting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: institutions, isLoading } = useQuery({
    queryKey: ['institutions'],
    queryFn: () => api.get<BankInstitution[]>('/banking/institutions?country=es'),
  });

  const filtered = (institutions ?? []).filter((bank) =>
    bank.name.toLowerCase().includes(search.toLowerCase()),
  );

  // Sort BBVA to top for sandbox testing
  const sorted = [...filtered].sort((a, b) => {
    const aIsBBVA = a.name.toLowerCase().includes('bbva');
    const bIsBBVA = b.name.toLowerCase().includes('bbva');
    if (aIsBBVA && !bIsBBVA) return -1;
    if (!aIsBBVA && bIsBBVA) return 1;
    return 0;
  });

  async function handleConnect(bank: BankInstitution) {
    setConnecting(bank.name);
    setError(null);
    try {
      const result = await api.post<{ url: string; authorization_id: string }>(
        '/banking/connect',
        { bank_name: bank.name, bank_country: bank.country },
      );
      window.location.assign(result.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al conectar con el banco.');
      setConnecting(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          href="/dashboard"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
        >
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Conectar banco</h1>
          <p className="text-sm text-gray-500">Selecciona tu entidad bancaria para continuar</p>
        </div>
      </div>

      {/* Sandbox callout */}
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        <strong>Entorno sandbox:</strong> usa <strong>BBVA</strong> para probar la conexión Open
        Banking con datos de prueba.
      </div>

      {/* Search */}
      <div className="relative">
        <Search
          size={15}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
        />
        <input
          type="text"
          placeholder="Buscar banco..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-xl border border-gray-200 bg-white py-2.5 pl-9 pr-4 text-sm outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-shadow"
        />
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Bank grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={28} className="animate-spin text-amber-400" />
        </div>
      ) : sorted.length === 0 ? (
        <p className="py-16 text-center text-sm text-gray-400">
          {search ? 'No se encontraron bancos.' : 'No hay bancos disponibles.'}
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {sorted.map((bank) => {
            const isBBVA = bank.name.toLowerCase().includes('bbva');
            const isConnecting = connecting === bank.name;
            return (
              <button
                key={`${bank.name}-${bank.country}`}
                onClick={() => handleConnect(bank)}
                disabled={connecting !== null}
                className={`flex items-center gap-4 rounded-xl border bg-white px-4 py-4 text-left transition-all hover:border-amber-300 hover:shadow-sm disabled:opacity-60 ${
                  isBBVA ? 'border-amber-300 ring-1 ring-amber-100' : 'border-gray-200'
                }`}
              >
                {bank.logo ? (
                  <Image
                    src={bank.logo}
                    alt={bank.name}
                    width={36}
                    height={36}
                    className="rounded-lg object-contain"
                    unoptimized
                  />
                ) : (
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-100">
                    <Building2 size={16} className="text-gray-400" />
                  </div>
                )}

                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">{bank.name}</p>
                  {isBBVA && (
                    <p className="mt-0.5 text-xs font-medium text-amber-600">
                      Recomendado para sandbox
                    </p>
                  )}
                </div>

                {isConnecting && (
                  <Loader2 size={15} className="shrink-0 animate-spin text-amber-500" />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
