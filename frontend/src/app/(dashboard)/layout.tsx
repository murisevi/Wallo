'use client';

import { useEffect, type ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { LogOut } from 'lucide-react';
import { useAuth } from '@/providers/auth-provider';
import NavLinkWithPrefetch from '@/components/features/NavLinkWithPrefetch';
import { api } from '@/lib/api';
import type { Dashboard, TransactionList } from '@/types';

const navLinks: {
  href: string;
  label: string;
  prefetch?: { queryKey: string[]; queryFn: () => Promise<unknown> }[];
}[] = [
  {
    href: '/dashboard',
    label: 'Dashboard',
    prefetch: [
      { queryKey: ['dashboard'], queryFn: () => api.get<Dashboard>('/dashboard/') },
    ],
  },
  {
    href: '/transactions',
    label: 'Transacciones',
    prefetch: [
      {
        queryKey: ['transactions', 'page:1', 'pageSize:20'],
        queryFn: () => api.get<TransactionList>('/transactions/?page=1&page_size=20'),
      },
    ],
  },
  { href: '/budgets', label: 'Presupuestos' },
  { href: '/reports', label: 'Informes' },
  { href: '/settings', label: 'Configuración' },
];

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#e8f0f8] border-t-[#0060ad]" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  const initials = user?.name
    ? user.name
        .split(' ')
        .map((w) => w[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : '?';

  return (
    <div className="flex min-h-full flex-col">
      {/* Top navigation */}
      <header className="sticky top-0 z-20 bg-white/90 backdrop-blur-md shadow-[0_1px_0_rgba(48,51,51,0.06)]">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Logo + nav links */}
          <div className="flex items-center gap-8">
            <span className="text-xl font-extrabold tracking-tight text-[#0060ad]">Wallo</span>
            <nav className="hidden sm:flex items-center gap-1">
              {navLinks.map(({ href, label, prefetch }) => {
                const isActive = pathname === href || pathname.startsWith(href + '/');
                return (
                  <NavLinkWithPrefetch
                    key={href}
                    href={href}
                    prefetchConfig={prefetch}
                    className={`relative px-3 py-4 text-sm font-medium transition-colors ${
                      isActive
                        ? 'text-[#0060ad] after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-[#0060ad] after:rounded-t-full'
                        : 'text-[#5d605f] hover:text-[#303333]'
                    }`}
                  >
                    {label}
                  </NavLinkWithPrefetch>
                );
              })}
            </nav>
          </div>

          {/* User info + logout */}
          <div className="flex items-center gap-3">
            <span className="hidden text-sm font-medium text-[#303333] sm:block">{user?.name}</span>
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#e8f0f8] text-xs font-bold text-[#0060ad]">
              {initials}
            </div>
            <button
              onClick={logout}
              title="Cerrar sesión"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-[#5d605f] hover:bg-[#f3f4f3] hover:text-[#303333] transition-colors"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>

        {/* Mobile nav */}
        <div className="flex sm:hidden border-t border-[#f3f4f3] px-4">
          {navLinks.map(({ href, label, prefetch }) => {
            const isActive = pathname === href || pathname.startsWith(href + '/');
            return (
              <NavLinkWithPrefetch
                key={href}
                href={href}
                prefetchConfig={prefetch}
                className={`flex-1 py-2 text-center text-xs font-medium transition-colors ${
                  isActive ? 'text-[#0060ad] border-b-2 border-[#0060ad]' : 'text-[#5d605f]'
                }`}
              >
                {label}
              </NavLinkWithPrefetch>
            );
          })}
        </div>
      </header>

      {/* Page content */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
        {children}
      </main>

      <footer className="py-6 text-center text-xs text-[#5d605f]">© 2026 Wallo.</footer>
    </div>
  );
}
