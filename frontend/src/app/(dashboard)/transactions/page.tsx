'use client';

import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Pencil,
  X,
  ShoppingCart,
  Utensils,
  Car,
  Home,
  Heart,
  Shirt,
  BookOpen,
  Repeat,
  TrendingUp,
  CreditCard,
  Calendar,
} from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTransactions } from '@/hooks/useTransactions';
import { useCategories } from '@/hooks/useCategories';
import { useAccounts } from '@/hooks/useAccounts';
import { api, categoryApi } from '@/lib/api';
import { CategoryBadge } from '@/components/features/CategoryBadge';
import type { Transaction } from '@/types';
import type { Category } from '@/types/categories';

const PAGE_SIZE = 20;

// ─── Category icon map (lucide icon name → component) ───────────────────────

const ICON_MAP: Record<string, React.ElementType> = {
  'shopping-cart': ShoppingCart,
  utensils: Utensils,
  car: Car,
  home: Home,
  heart: Heart,
  shirt: Shirt,
  book: BookOpen,
  repeat: Repeat,
  'trending-up': TrendingUp,
};

// ─── Category colour map (by name slug) ──────────────────────────────────────

const CATEGORY_COLOURS: Record<string, { bg: string; text: string; iconBg: string; iconColor: string }> = {
  'alimentación': {
    bg: 'bg-green-50', text: 'text-green-800',
    iconBg: 'bg-green-100', iconColor: 'text-green-600',
  },
  'ocio y cenas': {
    bg: 'bg-blue-50', text: 'text-blue-800',
    iconBg: 'bg-blue-100', iconColor: 'text-blue-600',
  },
  'transporte': {
    bg: 'bg-orange-50', text: 'text-orange-800',
    iconBg: 'bg-orange-100', iconColor: 'text-orange-500',
  },
  'hogar y servicios': {
    bg: 'bg-teal-50', text: 'text-teal-800',
    iconBg: 'bg-teal-100', iconColor: 'text-teal-600',
  },
  'salud': {
    bg: 'bg-rose-50', text: 'text-rose-800',
    iconBg: 'bg-rose-100', iconColor: 'text-rose-500',
  },
  'ropa': {
    bg: 'bg-purple-50', text: 'text-purple-800',
    iconBg: 'bg-purple-100', iconColor: 'text-purple-500',
  },
  'educación': {
    bg: 'bg-indigo-50', text: 'text-indigo-800',
    iconBg: 'bg-indigo-100', iconColor: 'text-indigo-500',
  },
  'suscripciones': {
    bg: 'bg-amber-50', text: 'text-amber-800',
    iconBg: 'bg-amber-100', iconColor: 'text-amber-500',
  },
};

const DEFAULT_EXPENSE_COLOURS = {
  bg: 'bg-[#f3f4f3]', text: 'text-[#5d605f]',
  iconBg: 'bg-[#f3f4f3]', iconColor: 'text-[#5d605f]',
};

const INCOME_COLOURS = {
  bg: 'bg-emerald-50', text: 'text-emerald-800',
  iconBg: 'bg-emerald-100', iconColor: 'text-emerald-600',
};

function getCategoryColours(name: string | null, isCredit: boolean) {
  if (!name) return isCredit ? INCOME_COLOURS : DEFAULT_EXPENSE_COLOURS;
  return CATEGORY_COLOURS[name.toLowerCase()] ?? DEFAULT_EXPENSE_COLOURS;
}

function getCategoryIcon(icon: string | null): React.ElementType {
  if (!icon) return CreditCard;
  return ICON_MAP[icon.toLowerCase()] ?? CreditCard;
}

// ─── Euro formatter ──────────────────────────────────────────────────────────

function formatEuro(amount: string, currency: string): string {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Math.abs(parseFloat(amount)));
}

// ─── Toast ───────────────────────────────────────────────────────────────────

interface ToastState {
  message: string;
  type: 'success' | 'error';
}

function Toast({ toast, onDismiss }: { toast: ToastState; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 3000);
    return () => clearTimeout(t);
  }, [onDismiss]);

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-xl px-5 py-3 shadow-lg text-sm font-semibold text-white transition-all ${
        toast.type === 'success' ? 'bg-[#1a6b3c]' : 'bg-red-600'
      }`}
    >
      {toast.message}
      <button onClick={onDismiss} className="opacity-70 hover:opacity-100">
        <X size={14} />
      </button>
    </div>
  );
}

// ─── Category edit modal ─────────────────────────────────────────────────────

interface CategoryModalProps {
  transaction: Transaction;
  categories: Category[];
  onClose: () => void;
  onSaved: (txn: Transaction) => void;
}

function CategoryModal({ transaction, categories, onClose, onSaved }: CategoryModalProps) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string | null>(transaction.category_id ?? null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: (categoryId: string | null) => {
      if (categoryId === null) {
        // Clearing the category: direct PATCH on the transaction (no active-learning event)
        return api.patch<Transaction>(`/transactions/${transaction.id}`, { category_id: null });
      }
      // Setting a category: goes through the active-learning endpoint which logs
      // a CategoryCorrection and upserts the merchant mapping.
      // Cast to Transaction so onSaved receives a compatible type; the list is
      // refreshed via invalidateQueries so the exact shape doesn't matter here.
      return categoryApi.correctTransactionCategory(transaction.id, categoryId) as unknown as Promise<Transaction>;
    },
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      onSaved(updated);
      onClose();
    },
  });

  function handleOverlayClick(e: React.MouseEvent) {
    if (e.target === overlayRef.current) onClose();
  }

  const isCredit = transaction.credit_debit_indicator === 'CRDT';

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 backdrop-blur-sm"
    >
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl">
        {/* Header */}
        <div className="mb-4 flex items-start justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-[#5d605f]">
              Editar categoría
            </p>
            <p className="mt-0.5 text-sm font-semibold text-[#303333] truncate max-w-[240px]">
              {transaction.description ?? transaction.creditor_name ?? transaction.debtor_name ?? 'Transacción'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-[#5d605f] hover:bg-[#f3f4f3] hover:text-[#303333] transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Category list */}
        <div className="max-h-72 space-y-1.5 overflow-y-auto">
          {/* "Sin categoría" option */}
          <button
            onClick={() => setSelected(null)}
            className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-colors ${
              selected === null
                ? 'bg-[#0060ad]/10 text-[#0060ad] font-semibold ring-1 ring-[#0060ad]/20'
                : 'hover:bg-[#f3f4f3] text-[#5d605f]'
            }`}
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#f3f4f3]">
              <CreditCard size={14} className="text-[#5d605f]" />
            </div>
            Sin categoría
          </button>

          {categories
            .filter((c) => (isCredit ? c.type === 'income' : c.type === 'expense'))
            .concat(categories.filter((c) => (isCredit ? c.type === 'expense' : c.type === 'income')))
            .map((cat) => {
              const Icon = getCategoryIcon(cat.icon);
              const colours = getCategoryColours(cat.name, false);
              const isActive = selected === cat.id;
              return (
                <button
                  key={cat.id}
                  onClick={() => setSelected(cat.id)}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-colors ${
                    isActive
                      ? 'bg-[#0060ad]/10 text-[#0060ad] font-semibold ring-1 ring-[#0060ad]/20'
                      : 'hover:bg-[#f3f4f3] text-[#303333]'
                  }`}
                >
                  <div
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${colours.iconBg}`}
                  >
                    <Icon size={14} className={colours.iconColor} />
                  </div>
                  <span className="flex-1">{cat.name}</span>
                  {cat.is_custom && (
                    <span className="text-[10px] font-medium text-[#5d605f] opacity-60">custom</span>
                  )}
                </button>
              );
            })}
        </div>

        {/* Actions */}
        <div className="mt-5 flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 rounded-xl bg-[#f3f4f3] py-2.5 text-sm font-medium text-[#303333] hover:bg-[#edeeed] transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={() => mutation.mutate(selected)}
            disabled={mutation.isPending}
            className="flex-1 rounded-xl bg-gradient-to-r from-[#0060ad] to-[#68abff] py-2.5 text-sm font-bold text-white hover:opacity-90 disabled:opacity-60 transition-all"
          >
            {mutation.isPending ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
        {mutation.isError && (
          <p className="mt-2 text-center text-xs text-red-600">
            Error al guardar. Inténtalo de nuevo.
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Table row ───────────────────────────────────────────────────────────────

interface TableRowProps {
  txn: Transaction;
  onEdit: (txn: Transaction) => void;
}

function TableRow({ txn, onEdit }: TableRowProps) {
  const isCredit = txn.credit_debit_indicator === 'CRDT';
  const label =
    txn.description ?? txn.creditor_name ?? txn.debtor_name ?? 'Transacción';

  const formattedDate = new Date(txn.date + 'T00:00:00').toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  const formattedAmount = formatEuro(txn.amount, txn.currency);

  const colours = getCategoryColours(txn.category_name, isCredit);
  const Icon = isCredit
    ? TrendingUp
    : getCategoryIcon(txn.category_icon);

  const accountDisplay = txn.account_iban
    ? `·· ${txn.account_iban.slice(-4)}`
    : '—';

  return (
    <tr className="group border-b border-[#f3f4f3] last:border-0 hover:bg-[#faf9f8] transition-colors">
      {/* Date */}
      <td className="py-4 pl-6 pr-4 text-sm text-[#5d605f] whitespace-nowrap">
        {formattedDate}
      </td>

      {/* Merchant */}
      <td className="py-4 px-4 max-w-[220px]">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${
              isCredit ? INCOME_COLOURS.iconBg : colours.iconBg
            }`}
          >
            <Icon
              size={15}
              className={isCredit ? INCOME_COLOURS.iconColor : colours.iconColor}
            />
          </div>
          <span
            title={label}
            className="truncate text-sm font-semibold text-[#303333]"
          >
            {label}
          </span>
        </div>
      </td>

      {/* Category badge */}
      <td className="py-4 px-4">
        {txn.category ? (
          <CategoryBadge
            name={txn.category.name}
            color={txn.category.color}
            confidence={txn.confidence_score}
            method={txn.categorization_method}
            onClick={() => onEdit(txn)}
          />
        ) : txn.category_name ? (
          // Fallback: name string without color object (shouldn't happen with new backend)
          <span className="inline-block rounded-full bg-[#f3f4f3] px-3 py-1 text-xs font-semibold text-[#5d605f]">
            {txn.category_name}
          </span>
        ) : (
          <button
            onClick={() => onEdit(txn)}
            className="text-xs text-[#5d605f] hover:text-[#0060ad] transition-colors"
          >
            + Categorizar
          </button>
        )}
      </td>

      {/* Account */}
      <td className="py-4 px-4 text-sm text-[#5d605f] whitespace-nowrap">
        {accountDisplay}
      </td>

      {/* Amount */}
      <td
        className={`py-4 px-4 text-right text-sm font-bold tabular-nums ${
          isCredit ? 'text-[#1a6b3c]' : 'text-red-500'
        }`}
      >
        {isCredit ? '+ ' : '- '}{formattedAmount}
      </td>

      {/* Actions */}
      <td className="py-4 pl-4 pr-6 text-right">
        <button
          onClick={() => onEdit(txn)}
          title="Editar categoría"
          className="inline-flex items-center gap-1.5 rounded-lg bg-[#f3f4f3] px-3 py-1.5 text-xs font-medium text-[#5d605f] opacity-0 group-hover:opacity-100 hover:bg-[#edeeed] hover:text-[#303333] transition-all"
        >
          <Pencil size={12} />
          Editar
        </button>
      </td>
    </tr>
  );
}

// ─── Skeleton row ─────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr className="border-b border-[#f3f4f3]">
      <td className="py-4 pl-6 pr-4">
        <div className="h-4 w-24 animate-pulse rounded-full bg-[#f3f4f3]" />
      </td>
      <td className="py-4 px-4">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 animate-pulse rounded-full bg-[#f3f4f3]" />
          <div className="h-4 w-36 animate-pulse rounded-full bg-[#f3f4f3]" />
        </div>
      </td>
      <td className="py-4 px-4">
        <div className="h-6 w-24 animate-pulse rounded-full bg-[#f3f4f3]" />
      </td>
      <td className="py-4 px-4">
        <div className="h-4 w-16 animate-pulse rounded-full bg-[#f3f4f3]" />
      </td>
      <td className="py-4 px-4">
        <div className="ml-auto h-4 w-20 animate-pulse rounded-full bg-[#f3f4f3]" />
      </td>
      <td className="py-4 pl-4 pr-6" />
    </tr>
  );
}

// ─── Pagination ───────────────────────────────────────────────────────────────

interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPage: (p: number) => void;
}

function Pagination({ page, totalPages, total, pageSize, onPage }: PaginationProps) {
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  // Build visible page numbers: [1] ... [prev] [cur] [next] ... [last]
  const pages: (number | '...')[] = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page > 3) pages.push('...');
    for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) {
      pages.push(i);
    }
    if (page < totalPages - 2) pages.push('...');
    pages.push(totalPages);
  }

  return (
    <div className="flex flex-col items-center gap-3 border-t border-[#f3f4f3] px-6 py-4 sm:flex-row sm:justify-between">
      <p className="text-xs text-[#5d605f]">
        Mostrando{' '}
        <strong className="text-[#303333]">
          {from} – {to}
        </strong>{' '}
        de <strong className="text-[#303333]">{total}</strong> transacciones
      </p>

      <div className="flex items-center gap-1">
        <button
          onClick={() => onPage(Math.max(1, page - 1))}
          disabled={page === 1}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#f3f4f3] text-[#5d605f] hover:bg-[#f3f4f3] disabled:opacity-40 transition-colors"
        >
          <ChevronLeft size={15} />
        </button>

        {pages.map((p, i) =>
          p === '...' ? (
            <span key={`ellipsis-${i}`} className="px-1 text-xs text-[#5d605f]">
              …
            </span>
          ) : (
            <button
              key={p}
              onClick={() => onPage(p as number)}
              className={`flex h-8 w-8 items-center justify-center rounded-lg text-sm font-medium transition-colors ${
                page === p
                  ? 'bg-[#0060ad] text-white shadow-sm'
                  : 'text-[#5d605f] hover:bg-[#f3f4f3]'
              }`}
            >
              {p}
            </button>
          ),
        )}

        <button
          onClick={() => onPage(Math.min(totalPages, page + 1))}
          disabled={page === totalPages}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#f3f4f3] text-[#5d605f] hover:bg-[#f3f4f3] disabled:opacity-40 transition-colors"
        >
          <ChevronRight size={15} />
        </button>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TransactionsPage() {
  const searchParams = useSearchParams();

  // URL params injected from /reports category click
  const initialCategoryId = searchParams.get('category_id') ?? '';
  const initialDateFrom = searchParams.get('date_from') ?? '';
  const initialDateTo = searchParams.get('date_to') ?? '';

  // ── Applied filters (trigger fetch) ───────────────────────────────────────
  const [page, setPage] = useState(1);
  const [appliedFilters, setAppliedFilters] = useState<{
    search: string;
    categoryId: string;
    accountId: string;
    dateFrom: string;
    dateTo: string;
  }>({
    search: '',
    categoryId: initialCategoryId,
    accountId: '',
    dateFrom: initialDateFrom,
    dateTo: initialDateTo,
  });

  // ── Pending (form) filters ─────────────────────────────────────────────────
  const [pendingSearch, setPendingSearch] = useState('');
  const [pendingCategory, setPendingCategory] = useState(initialCategoryId);
  const [pendingAccount, setPendingAccount] = useState('');
  const [pendingDateFrom, setPendingDateFrom] = useState(initialDateFrom);
  const [pendingDateTo, setPendingDateTo] = useState(initialDateTo);

  // ── Editing modal ──────────────────────────────────────────────────────────
  const [editingTxn, setEditingTxn] = useState<Transaction | null>(null);

  // ── Toast ──────────────────────────────────────────────────────────────────
  const [toast, setToast] = useState<ToastState | null>(null);

  // ── Data ───────────────────────────────────────────────────────────────────
  const { data, isLoading, isError, refetch } = useTransactions({
    page,
    pageSize: PAGE_SIZE,
    search: appliedFilters.search || undefined,
    categoryId: appliedFilters.categoryId || undefined,
    accountId: appliedFilters.accountId || undefined,
    dateFrom: appliedFilters.dateFrom || undefined,
    dateTo: appliedFilters.dateTo || undefined,
  });

  const { data: categories } = useCategories();
  const { data: accounts } = useAccounts();

  const totalPages = data?.total_pages ?? 1;

  // ── Handlers ───────────────────────────────────────────────────────────────

  function handleApply(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedFilters({
      search: pendingSearch.trim(),
      categoryId: pendingCategory,
      accountId: pendingAccount,
      dateFrom: pendingDateFrom,
      dateTo: pendingDateTo,
    });
  }

  function handleClearFilters() {
    setPendingSearch('');
    setPendingCategory('');
    setPendingAccount('');
    setPendingDateFrom('');
    setPendingDateTo('');
    setPage(1);
    setAppliedFilters({ search: '', categoryId: '', accountId: '', dateFrom: '', dateTo: '' });
  }

  const hasActiveFilters =
    appliedFilters.search ||
    appliedFilters.categoryId ||
    appliedFilters.accountId ||
    appliedFilters.dateFrom ||
    appliedFilters.dateTo;

  function handleCategorySaved(updated: Transaction) {
    setToast({ message: 'Categoría actualizada', type: 'success' });
    void updated; // query is already invalidated by mutation
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <>
      {/* Toast notification */}
      {toast && <Toast toast={toast} onDismiss={() => setToast(null)} />}

      {/* Category edit modal */}
      {editingTxn && categories && (
        <CategoryModal
          transaction={editingTxn}
          categories={categories}
          onClose={() => setEditingTxn(null)}
          onSaved={handleCategorySaved}
        />
      )}

      <div className="space-y-6">
        {/* Page header */}
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-[#303333]">
            Historial de Transacciones
          </h1>
          <p className="mt-1 text-sm text-[#5d605f]">
            Gestiona y revisa todos tus movimientos financieros en un solo lugar.
          </p>
        </div>

        {/* ── Filter bar ─────────────────────────────────────────────────── */}
        <form
          onSubmit={handleApply}
          className="rounded-2xl bg-white p-5 shadow-[0_2px_12px_rgba(48,51,51,0.06)]"
        >
          <div className="flex flex-wrap gap-3">
            {/* Search */}
            <div className="min-w-[180px] flex-1">
              <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
                Buscador
              </label>
              <div className="relative">
                <Search
                  size={14}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#5d605f]"
                />
                <input
                  type="text"
                  placeholder="Comercio o concepto…"
                  value={pendingSearch}
                  onChange={(e) => setPendingSearch(e.target.value)}
                  className="w-full rounded-xl bg-[#f3f4f3] py-2.5 pl-9 pr-3 text-sm text-[#303333] placeholder:text-[#5d605f]/60 outline-none focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
                />
              </div>
            </div>

            {/* Category */}
            <div className="min-w-[160px] flex-1">
              <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
                Categoría
              </label>
              <select
                value={pendingCategory}
                onChange={(e) => setPendingCategory(e.target.value)}
                className="w-full rounded-xl bg-[#f3f4f3] py-2.5 pl-3 pr-8 text-sm text-[#303333] outline-none focus:ring-2 focus:ring-[#0060ad]/20 transition-all appearance-none"
              >
                <option value="">Todas</option>
                <option value="uncategorized">Sin categoría</option>
                {(categories ?? []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Account */}
            <div className="min-w-[160px] flex-1">
              <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
                Cuenta
              </label>
              <select
                value={pendingAccount}
                onChange={(e) => setPendingAccount(e.target.value)}
                className="w-full rounded-xl bg-[#f3f4f3] py-2.5 pl-3 pr-8 text-sm text-[#303333] outline-none focus:ring-2 focus:ring-[#0060ad]/20 transition-all appearance-none"
              >
                <option value="">Todas</option>
                {(accounts ?? []).map((acc) => {
                  const label = acc.iban
                    ? `·· ${acc.iban.slice(-4)}`
                    : (acc.name ?? acc.id);
                  return (
                    <option key={acc.id} value={acc.id}>
                      {label}
                    </option>
                  );
                })}
              </select>
            </div>

            {/* Date from */}
            <div className="min-w-[140px]">
              <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
                Desde
              </label>
              <div className="relative">
                <Calendar
                  size={14}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#5d605f]"
                />
                <input
                  type="date"
                  value={pendingDateFrom}
                  onChange={(e) => setPendingDateFrom(e.target.value)}
                  className="w-full rounded-xl bg-[#f3f4f3] py-2.5 pl-9 pr-3 text-sm text-[#303333] outline-none focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
                />
              </div>
            </div>

            {/* Date to */}
            <div className="min-w-[140px]">
              <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
                Hasta
              </label>
              <div className="relative">
                <Calendar
                  size={14}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#5d605f]"
                />
                <input
                  type="date"
                  value={pendingDateTo}
                  onChange={(e) => setPendingDateTo(e.target.value)}
                  className="w-full rounded-xl bg-[#f3f4f3] py-2.5 pl-9 pr-3 text-sm text-[#303333] outline-none focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-end gap-2">
              <button
                type="submit"
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#0060ad] to-[#68abff] px-5 py-2.5 text-sm font-bold text-white hover:opacity-90 transition-all whitespace-nowrap"
              >
                <SlidersHorizontal size={14} />
                Aplicar
              </button>
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={handleClearFilters}
                  className="rounded-xl bg-[#f3f4f3] px-4 py-2.5 text-sm font-medium text-[#303333] hover:bg-[#edeeed] transition-colors whitespace-nowrap"
                >
                  Limpiar
                </button>
              )}
            </div>
          </div>
        </form>

        {/* ── Error state ─────────────────────────────────────────────────── */}
        {isError && (
          <div className="rounded-2xl bg-white px-6 py-8 text-center shadow-[0_4px_16px_rgba(48,51,51,0.06)]">
            <p className="text-sm font-medium text-red-600">
              No se pudieron cargar las transacciones.
            </p>
            <button
              onClick={() => refetch()}
              className="mt-3 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] px-5 py-2.5 text-sm font-bold text-white hover:opacity-90 transition-all"
            >
              <RefreshCw size={13} />
              Reintentar
            </button>
          </div>
        )}

        {/* ── Transaction table ────────────────────────────────────────────── */}
        {!isError && (
          <div className="overflow-hidden rounded-2xl bg-white shadow-[0_4px_16px_rgba(48,51,51,0.06)]">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px]">
                <thead>
                  <tr className="border-b border-[#f3f4f3]">
                    <th className="py-3.5 pl-6 pr-4 text-left text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
                      Fecha
                    </th>
                    <th className="py-3.5 px-4 text-left text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
                      Comercio
                    </th>
                    <th className="py-3.5 px-4 text-left text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
                      Categoría
                    </th>
                    <th className="py-3.5 px-4 text-left text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
                      Cuenta
                    </th>
                    <th className="py-3.5 px-4 text-right text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
                      Importe
                    </th>
                    <th className="py-3.5 pl-4 pr-6 text-right text-[10px] font-bold uppercase tracking-widest text-[#5d605f]">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    Array.from({ length: 8 }, (_, i) => <SkeletonRow key={i} />)
                  ) : (data?.transactions.length ?? 0) === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-14 text-center">
                        <p className="text-sm text-[#5d605f]">
                          {hasActiveFilters
                            ? 'No se encontraron transacciones con los filtros actuales.'
                            : 'Aún no hay transacciones. Conecta un banco para empezar.'}
                        </p>
                      </td>
                    </tr>
                  ) : (
                    data?.transactions.map((txn) => (
                      <TableRow key={txn.id} txn={txn} onEdit={setEditingTxn} />
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {!isLoading && data && data.total > 0 && (
              <Pagination
                page={page}
                totalPages={totalPages}
                total={data.total}
                pageSize={PAGE_SIZE}
                onPage={setPage}
              />
            )}
          </div>
        )}

        {/* ── Footer ──────────────────────────────────────────────────────── */}
        <footer className="border-t border-[#f3f4f3] pt-6 pb-2">
          <div className="flex flex-col items-center gap-2 text-center sm:flex-row sm:justify-between">
            <p className="text-xs text-[#5d605f]">
              © 2024 Wallo Personal Finance.{' '}
              <span className="italic">The Digital Sanctuary.</span>
            </p>
            <div className="flex gap-4 text-xs text-[#5d605f]">
              <a href="#" className="hover:text-[#303333] transition-colors">Privacidad</a>
              <a href="#" className="hover:text-[#303333] transition-colors">Términos</a>
              <a href="#" className="hover:text-[#303333] transition-colors">Soporte</a>
              <a href="#" className="hover:text-[#303333] transition-colors">Contacto</a>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}
