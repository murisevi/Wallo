'use client';

import Link from 'next/link';
import { useQueryClient } from '@tanstack/react-query';
import type { ReactNode } from 'react';

interface PrefetchConfig {
  queryKey: string[];
  queryFn: () => Promise<unknown>;
}

interface NavLinkWithPrefetchProps {
  href: string;
  className?: string;
  prefetchConfig?: PrefetchConfig[];
  children: ReactNode;
}

export default function NavLinkWithPrefetch({
  href,
  className,
  prefetchConfig,
  children,
}: NavLinkWithPrefetchProps) {
  const queryClient = useQueryClient();

  function handleMouseEnter() {
    if (!prefetchConfig?.length) return;
    for (const config of prefetchConfig) {
      queryClient.prefetchQuery({
        queryKey: config.queryKey,
        queryFn: config.queryFn,
        staleTime: 1000 * 60, // only prefetch if data is older than 1 min
      });
    }
  }

  return (
    <Link href={href} className={className} onMouseEnter={handleMouseEnter}>
      {children}
    </Link>
  );
}
