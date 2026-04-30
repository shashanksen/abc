'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { PublicTopbar } from '@/components/PublicTopbar';
import { ApiError } from '@/lib/errors';

export default function RegisterPage() {
  const { register } = useAuth();
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setSubmitting(true);
    try {
      await register(email, fullName, password);
    } catch (e: any) {
      setError(e instanceof ApiError ? e.userMessage() : (e.message || 'Registration failed'));
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
            <div className="hero-kicker">Provision access</div>
            <h1 className="auth-title">Create an account before module approval.</h1>
            <p className="auth-copy">
              Registration uses the live backend endpoint. After sign-in, users request module access and admins review
              the request from the console.
            </p>
          </section>

          <section className="auth-card">
            <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '4px' }}>Create account</h2>
            <p className="page-subtitle" style={{ marginBottom: '20px' }}>You can request module access after sign-in.</p>

            <form onSubmit={submit}>
              <div className="form-group">
                <label className="form-label">Full name</label>
                <input className="form-input" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input className="form-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>
              <div className="form-group">
                <label className="form-label">Password</label>
                <input className="form-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
                <div className="form-hint">Minimum length is 8 characters.</div>
              </div>

              {error && <div className="alert alert-error">{error}</div>}

              <button type="submit" className="btn btn-primary" disabled={submitting} style={{ width: '100%' }}>
                {submitting ? 'Creating...' : 'Create account'}
              </button>
            </form>

            <p className="page-subtitle" style={{ marginTop: '20px' }}>
              Already have an account? <Link href="/login" style={{ color: 'var(--accent-primary)' }}>Sign in</Link>
            </p>
          </section>
        </div>
      </main>
    </>
  );
}
