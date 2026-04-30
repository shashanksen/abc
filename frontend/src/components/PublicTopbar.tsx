'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { ThemeToggle } from '@/components/ThemeToggle';

function isActive(pathname: string, href: string) {
  if (href === '/') return pathname === '/';
  return pathname === href;
}

export function PublicTopbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <header className="topbar">
      <Link href="/" className="topbar-brand">
        CDP iSuite
      </Link>

      <nav className="topbar-nav app-nav">
        <Link href="/" className={`topbar-nav-item${isActive(pathname, '/') ? ' active' : ''}`}>
          Home
        </Link>
        {!user && (
          <>
            <Link href="/login" className={`topbar-nav-item${isActive(pathname, '/login') ? ' active' : ''}`}>
              Sign in
            </Link>
            <Link href="/register" className={`topbar-nav-item${isActive(pathname, '/register') ? ' active' : ''}`}>
              Register
            </Link>
          </>
        )}
      </nav>

      <div className="topbar-spacer" />

      <div className="topbar-actions">
        <ThemeToggle />
        {user ? (
          <>
            <Link href={user.is_admin ? '/admin' : '/dashboard'} className="btn btn-primary btn-sm">
              Open workspace
            </Link>
            <button type="button" className="btn btn-secondary btn-sm" onClick={logout}>
              Sign out
            </button>
          </>
        ) : (
          <Link href="/login" className="btn btn-primary btn-sm">
            Open workspace
          </Link>
        )}
      </div>
    </header>
  );
}