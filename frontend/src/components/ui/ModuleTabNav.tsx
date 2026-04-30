'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { moduleRegistry } from '@/lib/moduleRegistry';

interface ModuleTabNavProps {
  moduleCode: string;
}

export function ModuleTabNav({ moduleCode }: ModuleTabNavProps) {
  const pathname = usePathname();
  const cfg = moduleRegistry.get(moduleCode);

  if (!cfg) return null;

  return (
    <nav className="module-tab-nav" aria-label={`${cfg.name} navigation`}>
      {cfg.features.map((feature) => {
        const href = `${cfg.basePath}${feature.path}`.replace(/\/$/, '') || cfg.basePath;
        const active =
          (feature.path === '/' && pathname === cfg.basePath) ||
          (feature.path !== '/' && pathname.startsWith(href));

        return (
          <Link
            key={feature.code}
            href={href}
            className={`module-tab-link${active ? ' active' : ''}`}
          >
            {feature.name}
          </Link>
        );
      })}
    </nav>
  );
}