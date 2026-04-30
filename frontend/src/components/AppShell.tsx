'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState, type ReactNode } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { ThemeToggle } from '@/components/ThemeToggle';
import { modulesApi, type ModuleSummary } from '@/lib/coreApi';
import { getDemoModules, isDemoUser } from '@/lib/demoData';
import { moduleRegistry } from '@/lib/moduleRegistry';
import { ApiError } from '@/lib/errors';

interface Props {
  children: ReactNode;
  /** Force-show admin link even outside admin role (no-op if not admin) */
  showAdminNav?: boolean;
}

export function AppShell({ children, showAdminNav = false }: Props) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const demoSession = isDemoUser(user?.id);
  const [modules, setModules] = useState<ModuleSummary[]>([]);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  useEffect(() => {
    if (demoSession) {
      setModules(getDemoModules());
      setLoadErr(null);
      return;
    }

    modulesApi
      .list()
      .then(setModules)
      .catch((e) => {
        setLoadErr(e instanceof ApiError ? e.userMessage() : 'Failed to load modules');
      });
  }, [demoSession]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link href={user?.is_admin ? '/admin' : '/dashboard'} className="topbar-brand">
          CDP iSuite
        </Link>

        <nav className="topbar-nav app-nav">
          <Link href="/dashboard" className={`topbar-nav-item${isActive(pathname, '/dashboard') ? ' active' : ''}`}>
            Dashboard
          </Link>
          <Link href="/access/request" className={`topbar-nav-item${isActive(pathname, '/access/request') ? ' active' : ''}`}>
            Access
          </Link>
          <Link href="/settings" className={`topbar-nav-item${isActive(pathname, '/settings') ? ' active' : ''}`}>
            Settings
          </Link>
          {(user?.is_admin || showAdminNav) && (
            <Link href="/admin" className={`topbar-nav-item${isActive(pathname, '/admin') ? ' active' : ''}`}>
              Admin
            </Link>
          )}
          {modules.map((moduleItem) => {
            const cfg = moduleRegistry.get(moduleItem.code);
            if (!cfg) return null;

            return (
              <Link
                key={moduleItem.id}
                href={cfg.basePath}
                className={`topbar-nav-item${isActive(pathname, cfg.basePath) ? ' active' : ''}`}
              >
                {moduleItem.name}
              </Link>
            );
          })}
        </nav>

        <div className="topbar-spacer" />

        <div className="topbar-actions">
          <span className="app-user-chip">{user?.full_name}</span>
          <ThemeToggle />
          <button type="button" className="btn btn-secondary btn-sm" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>

      <main className="page-wrap">
        {loadErr && <div className="alert alert-error">{loadErr}</div>}
        {children}
      </main>
    </div>
  );
}

function isActive(pathname: string, href: string) {
  if (href === '/dashboard') return pathname === '/dashboard';
  return pathname === href || pathname.startsWith(`${href}/`);
}
