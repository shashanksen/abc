'use client';

import Link from 'next/link';
import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { PublicTopbar } from '@/components/PublicTopbar';
import { ApiError } from '@/lib/errors';

// Set to true to re-show the demo bypass UI for debugging.
// The underlying loginAsDemo() logic stays in useAuth even when false.
const SHOW_DEMO_BYPASS = false;

function LoginInner() {
  const router = useRouter();
  const { user, loading, login, loginAsDemo } = useAuth();
  const params = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (params.get('expired') === '1') {
      setError('Your session has expired. Please sign in again.');
    }
  }, [params]);

  useEffect(() => {
    if (loading || !user) return;
    router.replace(user.is_admin ? '/admin' : '/dashboard');
  }, [loading, router, user]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (e: any) {
      setError(e instanceof ApiError ? e.userMessage() : (e.message || 'Login failed'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <PublicTopbar />

      <main className="auth-shell">
        <div className="auth-grid">
          <section className="auth-panel">
            <div className="hero-kicker">CDP iSuite</div>
            <h1 className="auth-title">Sign in to the CDP workspace.</h1>
            <p className="auth-copy">
              Access your data quality, governance, and analytics modules from one place.
              Sign in with your CDP credentials to continue.
            </p>

            {SHOW_DEMO_BYPASS && (
              <div className="surface-list" style={{ marginTop: '24px' }}>
                <div className="surface-row">
                  <div>
                    <div className="surface-row-title">Real login</div>
                    <div className="surface-row-meta">Uses /api/auth/login and then fetches /api/auth/me.</div>
                  </div>
                  <span className="chip chip-success">Live</span>
                </div>
                <div className="surface-row">
                  <div>
                    <div className="surface-row-title">Demo admin bypass</div>
                    <div className="surface-row-meta">Drops you into the admin console for settings and approval workflow testing.</div>
                  </div>
                  <span className="chip chip-primary">Preview</span>
                </div>
                <div className="surface-row">
                  <div>
                    <div className="surface-row-title">Demo user bypass</div>
                    <div className="surface-row-meta">Lets you test the standard dashboard path without backend credentials.</div>
                  </div>
                  <span className="chip chip-info">Preview</span>
                </div>
              </div>
            )}
          </section>

          <section className="auth-card">
            <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '4px' }}>Welcome back</h2>
            <p className="page-subtitle" style={{ marginBottom: '20px' }}>Sign in to continue to your workspace.</p>

            <form onSubmit={submit}>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input className="form-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
              </div>
              <div className="form-group">
                <label className="form-label">Password</label>
                <input className="form-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </div>

              {error && <div className="alert alert-error">{error}</div>}

              <button type="submit" className="btn btn-primary" disabled={submitting} style={{ width: '100%' }}>
                {submitting ? 'Signing in...' : 'Sign in'}
              </button>
            </form>

            {SHOW_DEMO_BYPASS && (
              <div className="surface-list" style={{ marginTop: '20px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => loginAsDemo('admin')} style={{ width: '100%' }}>
                  Continue as demo admin
                </button>
                <button type="button" className="btn btn-ghost" onClick={() => loginAsDemo('user')} style={{ width: '100%', marginTop: '8px' }}>
                  Continue as demo analyst
                </button>
              </div>
            )}

            <p className="page-subtitle" style={{ marginTop: '20px' }}>
              New here? <Link href="/register" style={{ color: 'var(--accent-primary)' }}>Create an account</Link>
            </p>
          </section>
        </div>
      </main>
    </>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="page-wrap">Loading...</main>}>
      <LoginInner />
    </Suspense>
  );
}