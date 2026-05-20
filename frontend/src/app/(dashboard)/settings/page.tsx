'use client';

import { useState, useEffect, Suspense } from 'react';
import { Building2, ChevronDown, Loader2, Plus, X, Check } from 'lucide-react';
import Image from 'next/image';
import { useSearchParams } from 'next/navigation';
import { useAuth } from '@/providers/auth-provider';
import { useProfile, useUpdateProfile } from '@/hooks/useProfile';
import { useConnections, useDisconnectBank } from '@/hooks/useConnections';
import { api } from '@/lib/api';
import type { BankInstitution } from '@/types';
import type { BankConnection } from '@/types/settings';

// ─── Helpers ────────────────────────────────────────────────────────────────

function relativeTime(iso: string | null): string {
  if (!iso) return 'Nunca';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return mins <= 1 ? 'Hace un momento' : `Hace ${mins} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return hours === 1 ? 'Hace 1 hora' : `Hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return days === 1 ? 'Hace 1 día' : `Hace ${days} días`;
}

function isSynced(iso: string | null): boolean {
  if (!iso) return false;
  return Date.now() - new Date(iso).getTime() < 3_600_000; // < 1h
}

// ─── Toast ──────────────────────────────────────────────────────────────────

interface ToastProps {
  message: string;
  type: 'success' | 'error';
  onClose: () => void;
}

function Toast({ message, type, onClose }: ToastProps) {
  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-2xl px-5 py-3.5 text-sm font-medium shadow-lg transition-all ${
        type === 'success' ? 'bg-[#1a3a1a] text-white' : 'bg-red-600 text-white'
      }`}
    >
      {type === 'success' ? <Check size={15} /> : <X size={15} />}
      {message}
      <button onClick={onClose} className="ml-1 opacity-70 hover:opacity-100">
        <X size={13} />
      </button>
    </div>
  );
}

// ─── Section card ────────────────────────────────────────────────────────────

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-card">
      <h2 className="mb-5 text-base font-bold text-[#1a1a1a]">{title}</h2>
      {children}
    </div>
  );
}

// ─── Add Bank Modal ──────────────────────────────────────────────────────────

function AddBankModal({ onClose }: { onClose: () => void }) {
  const [search, setSearch] = useState('');
  const [connecting, setConnecting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [institutions, setInstitutions] = useState<BankInstitution[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<BankInstitution[]>('/banking/institutions?country=es')
      .then((data) => setInstitutions(data))
      .catch(() => setInstitutions([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = (institutions ?? []).filter((b) =>
    b.name.toLowerCase().includes(search.toLowerCase()),
  );

  async function handleConnect(bank: BankInstitution) {
    setConnecting(bank.name);
    setError(null);
    try {
      // Store where to return after the OAuth callback finishes.
      // The registered redirect_url in Enable Banking must be /banking/callback —
      // we use sessionStorage so that callback can redirect back here.
      sessionStorage.setItem('wallo:banking_return_to', '/settings');
      const result = await api.post<{ url: string; authorization_id: string }>(
        '/banking/connect',
        { bank_name: bank.name, bank_country: bank.country },
      );
      window.location.assign(result.url);
    } catch (err) {
      sessionStorage.removeItem('wallo:banking_return_to');
      setError(err instanceof Error ? err.message : 'Error al conectar con el banco.');
      setConnecting(null);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h3 className="text-base font-bold text-[#1a1a1a]">Añadir banco</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <div className="px-6 pt-4 pb-2">
          <input
            type="text"
            placeholder="Buscar banco…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl bg-[#F5F5F5] px-4 py-2.5 text-sm text-[#1a1a1a] placeholder:text-gray-400 outline-none"
          />
        </div>

        {error && (
          <div className="mx-6 mb-2 rounded-xl bg-red-50 px-4 py-2 text-xs text-red-600">
            {error}
          </div>
        )}

        <div className="max-h-72 overflow-y-auto px-6 pb-4">
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 size={24} className="animate-spin text-gray-400" />
            </div>
          ) : filtered.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">
              {search ? 'No se encontraron bancos.' : 'No hay bancos disponibles.'}
            </p>
          ) : (
            <div className="space-y-1.5 pt-1">
              {filtered.map((bank) => (
                <button
                  key={`${bank.name}-${bank.country}`}
                  onClick={() => handleConnect(bank)}
                  disabled={connecting !== null}
                  className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left hover:bg-[#F5F5F5] disabled:opacity-60 transition-colors"
                >
                  {bank.logo ? (
                    <Image src={bank.logo} alt={bank.name} width={28} height={28} className="rounded-lg object-contain" unoptimized />
                  ) : (
                    <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#F5F5F5]">
                      <Building2 size={14} className="text-gray-400" />
                    </div>
                  )}
                  <span className="flex-1 truncate text-sm font-medium text-[#1a1a1a]">{bank.name}</span>
                  {connecting === bank.name && <Loader2 size={14} className="animate-spin text-gray-400" />}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Disconnect Confirm Modal ────────────────────────────────────────────────

function DisconnectModal({
  connection,
  onConfirm,
  onCancel,
  isPending,
}: {
  connection: BankConnection;
  onConfirm: () => void;
  onCancel: () => void;
  isPending: boolean;
}) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl">
        <h3 className="text-base font-bold text-[#1a1a1a]">Desvincular banco</h3>
        <p className="mt-2 text-sm text-gray-500">
          ¿Seguro que quieres desvincular <strong>{connection.bank_name}</strong>? Tus transacciones
          históricas se conservarán.
        </p>
        <div className="mt-5 flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 rounded-xl border border-gray-200 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="flex-1 rounded-xl bg-red-600 py-2.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60 transition-colors"
          >
            {isPending ? <Loader2 size={15} className="mx-auto animate-spin" /> : 'Desvincular'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Skeleton ────────────────────────────────────────────────────────────────

function SkeletonSection() {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-card">
      <div className="mb-5 h-4 w-36 animate-pulse rounded-full bg-gray-100" />
      <div className="space-y-3">
        <div className="h-10 w-full animate-pulse rounded-xl bg-gray-100" />
        <div className="h-10 w-full animate-pulse rounded-xl bg-gray-100" />
      </div>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

function SettingsContent() {
  const { logout } = useAuth();
  const searchParams = useSearchParams();

  // Profile
  const { data: profile, isLoading: profileLoading } = useProfile();
  const updateProfile = useUpdateProfile();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [currency, setCurrency] = useState<'EUR' | 'USD' | 'GBP'>('EUR');

  useEffect(() => {
    if (profile) {
      setFullName(profile.full_name);
      setEmail(profile.email);
      setCurrency(profile.currency);
    }
  }, [profile]);

  // Connections
  const { data: connections, isLoading: connectionsLoading } = useConnections();
  const disconnectBank = useDisconnectBank();

  // UI state
  const [showAddBank, setShowAddBank] = useState(false);
  const [disconnectTarget, setDisconnectTarget] = useState<BankConnection | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [saving, setSaving] = useState(false);

  function showToast(message: string, type: 'success' | 'error') {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  }

  // Show success toast when returning from OAuth callback
  useEffect(() => {
    if (searchParams.get('connected') === '1') {
      showToast('Banco conectado correctamente', 'success');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSaveProfile() {
    setSaving(true);
    try {
      await updateProfile.mutateAsync({
        full_name: fullName,
        email,
        currency,
      });
      showToast('Perfil actualizado correctamente', 'success');
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Error al guardar el perfil', 'error');
    } finally {
      setSaving(false);
    }
  }

  async function handleDisconnect() {
    if (!disconnectTarget) return;
    try {
      await disconnectBank.mutateAsync(disconnectTarget.id);
      showToast('Banco desvinculado correctamente', 'success');
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Error al desvincular el banco', 'error');
    } finally {
      setDisconnectTarget(null);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-[#303333]">Configuración</h1>
        <p className="mt-1 text-sm text-[#5d605f]">
          Gestiona tu perfil y tus bancos conectados.
        </p>
      </div>

      {/* ── 1. Perfil Personal ─────────────────────────────────────────────── */}
      {profileLoading ? (
        <SkeletonSection />
      ) : (
        <SectionCard title="Perfil Personal">
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Nombre completo
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full rounded-xl bg-[#F5F5F5] px-4 py-2.5 text-sm text-[#1a1a1a] outline-none focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
                  placeholder="Tu nombre"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl bg-[#F5F5F5] px-4 py-2.5 text-sm text-[#1a1a1a] outline-none focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
                  placeholder="tu@email.com"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Moneda principal
              </label>
              <div className="relative">
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value as 'EUR' | 'USD' | 'GBP')}
                  className="w-full appearance-none rounded-xl bg-[#F5F5F5] px-4 py-2.5 text-sm text-[#1a1a1a] outline-none focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
                >
                  <option value="EUR">EUR — Euro</option>
                  <option value="USD">USD — Dólar estadounidense</option>
                  <option value="GBP">GBP — Libra esterlina</option>
                </select>
                <ChevronDown size={14} className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-gray-400" />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleSaveProfile}
                disabled={saving}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#0060ad] to-[#68abff] px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-60 transition-all"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                Guardar cambios
              </button>
            </div>
          </div>
        </SectionCard>
      )}

      {/* ── 2. Cuentas Conectadas ───────────────────────────────────────────── */}
      {connectionsLoading ? (
        <SkeletonSection />
      ) : (
        <SectionCard title="Cuentas Conectadas">
          <div className="space-y-3">
            {(connections ?? []).length === 0 ? (
              <p className="py-4 text-center text-sm text-gray-400">
                No tienes bancos conectados todavía.
              </p>
            ) : (
              (connections ?? []).map((conn) => {
                const synced = isSynced(conn.last_synced_at);
                const initial = conn.bank_name.charAt(0).toUpperCase();
                return (
                  <div
                    key={conn.id}
                    className="flex items-center gap-4 rounded-xl border border-gray-100 bg-[#FAFAFA] px-4 py-3"
                  >
                    {/* Bank icon */}
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#0060ad]/10 text-base font-bold text-[#0060ad]">
                      {initial}
                    </div>

                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-[#1a1a1a]">
                        {conn.bank_name}
                      </p>
                      <p className="text-xs text-gray-400">
                        {conn.accounts_count} cuenta{conn.accounts_count !== 1 ? 's' : ''}
                      </p>
                    </div>

                    {/* Status badge */}
                    <span
                      className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${
                        synced
                          ? 'bg-green-50 text-green-700'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {synced ? 'Sincronizado' : `Última vez: ${relativeTime(conn.last_synced_at)}`}
                    </span>

                    <button
                      onClick={() => setDisconnectTarget(conn)}
                      className="shrink-0 text-xs font-semibold text-[#0060ad] hover:underline"
                    >
                      Desvincular
                    </button>
                  </div>
                );
              })
            )}

            <button
              onClick={() => setShowAddBank(true)}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-[#0060ad]/30 py-3 text-sm font-semibold text-[#0060ad] hover:bg-[#0060ad]/5 transition-colors"
            >
              <Plus size={15} />
              Añadir banco
            </button>
          </div>
        </SectionCard>
      )}

      {/* ── 3. Sesión ───────────────────────────────────────────────────────── */}
      <SectionCard title="Sesión">
        <button
          onClick={logout}
          className="flex w-full items-center justify-center rounded-xl bg-red-600 px-5 py-3.5 text-sm font-bold text-white hover:bg-red-700 transition-colors"
        >
          Cerrar Sesión
        </button>
      </SectionCard>

      {/* ── Modals ──────────────────────────────────────────────────────────── */}
      {showAddBank && <AddBankModal onClose={() => setShowAddBank(false)} />}

      {disconnectTarget && (
        <DisconnectModal
          connection={disconnectTarget}
          onConfirm={handleDisconnect}
          onCancel={() => setDisconnectTarget(null)}
          isPending={disconnectBank.isPending}
        />
      )}

      {/* ── Toast ───────────────────────────────────────────────────────────── */}
      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={null}>
      <SettingsContent />
    </Suspense>
  );
}
