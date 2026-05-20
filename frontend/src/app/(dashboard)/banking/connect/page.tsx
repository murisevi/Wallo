'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Building2, Loader2 } from 'lucide-react';
import Image from 'next/image';
import { api } from '@/lib/api';
import type { BankInstitution } from '@/types';

export default function ConnectBankPage() {
  const [search, setSearch] = useState('');
  const [connecting, setConnecting] = useState<string | null>(null);
  const [connectError, setConnectError] = useState<string | null>(null);

  const {
    data: institutions,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['institutions'],
    queryFn: () => api.get<BankInstitution[]>('/banking/institutions?country=es'),
    staleTime: 0,   // always fetch fresh — list changes when backend reconnects
    retry: 1,
  });

  const filtered = (institutions ?? []).filter((bank) =>
    bank.name.toLowerCase().includes(search.toLowerCase()),
  );

  const sorted = [...filtered].sort((a, b) => {
    const aIsBBVA = a.name.toLowerCase().includes('bbva');
    const bIsBBVA = b.name.toLowerCase().includes('bbva');
    if (aIsBBVA && !bIsBBVA) return -1;
    if (!aIsBBVA && bIsBBVA) return 1;
    return 0;
  });

  async function handleConnect(bank: BankInstitution) {
    setConnecting(bank.name);
    setConnectError(null);
    try {
      const result = await api.post<{ url: string; authorization_id: string }>(
        '/banking/connect',
        { bank_name: bank.name, bank_country: bank.country },
      );
      window.location.assign(result.url);
    } catch (err) {
      setConnectError(err instanceof Error ? err.message : 'Error al conectar con el banco.');
      setConnecting(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-[#303333]">Conecta tu banco</h1>
        <p className="mt-1 text-sm text-[#5d605f]">Selecciona tu entidad bancaria para continuar</p>
      </div>

      {/* Sandbox callout */}
      <div className="rounded-2xl bg-amber-50 px-5 py-4 text-sm text-amber-800">
        <strong>Entorno sandbox:</strong> usa <strong>BBVA</strong> para probar la conexión Open
        Banking con datos de prueba.
      </div>

      {/* Search */}
      <div className="relative">
        <Search
          size={15}
          className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#5d605f]"
        />
        <input
          type="text"
          placeholder="Buscar banco…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-xl bg-[#f3f4f3] py-3 pl-10 pr-4 text-sm text-[#303333] placeholder:text-[#5d605f]/60 outline-none ring-1 ring-transparent focus:ring-2 focus:ring-amber-300 transition-all"
        />
      </div>

      {/* Error banner (connect action errors) */}
      {connectError && (
        <div className="rounded-2xl bg-red-50 px-5 py-4 text-sm text-red-700">{connectError}</div>
      )}

      {/* Bank grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={28} className="animate-spin text-amber-400" />
        </div>
      ) : isError ? (
        <div className="rounded-2xl bg-red-50 px-5 py-6 text-center">
          <p className="text-sm font-semibold text-red-700">
            No se pudieron cargar los bancos.
          </p>
          <p className="mt-1 text-xs text-red-600">
            {error instanceof Error ? error.message : 'Error desconocido'}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-4 rounded-xl bg-red-100 px-4 py-2 text-xs font-semibold text-red-700 hover:bg-red-200 transition-colors"
          >
            Reintentar
          </button>
        </div>
      ) : sorted.length === 0 ? (
        <p className="py-16 text-center text-sm text-[#5d605f]">
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
                className={`flex items-center gap-4 rounded-2xl bg-white px-5 py-4 text-left shadow-card-md transition-all hover:shadow-card-lg disabled:opacity-60 ${
                  isBBVA ? 'ring-2 ring-amber-300' : ''
                }`}
              >
                {bank.logo ? (
                  <Image
                    src={bank.logo}
                    alt={bank.name}
                    width={36}
                    height={36}
                    className="rounded-xl object-contain"
                    unoptimized
                  />
                ) : (
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#f3f4f3]">
                    <Building2 size={16} className="text-[#5d605f]" />
                  </div>
                )}

                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-[#303333]">{bank.name}</p>
                  {isBBVA && (
                    <p className="mt-0.5 text-xs font-semibold text-amber-600">
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
