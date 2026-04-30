'use client';

import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { PublicTopbar } from '@/components/PublicTopbar';

export default function HomePage() {
  const { user, loading } = useAuth();

  return (
    <>
      <PublicTopbar />

      <main className="page-wrap">
        <section className="hero">
          <div className="hero-panel">
            <div className="hero-kicker">Platform workspace</div>
            <h1 className="hero-title">Operate data quality and access from one control plane.</h1>
            <p className="hero-copy">
              CDP iSuite is the frontend shell for module-led platform work. It already speaks to the FastAPI auth,
              admin, access, and DQ endpoints, and now includes a preview path for UI testing before every backend
              workflow is complete.
            </p>

            <div className="hero-actions">
              {loading ? (
                <span className="chip chip-neutral">Checking session...</span>
              ) : user ? (
                <>
                  <Link href={user.is_admin ? '/admin' : '/dashboard'} className="btn btn-primary">
                    Open workspace
                  </Link>
                  <Link href="/settings" className="btn btn-secondary">
                    View settings
                  </Link>
                </>
              ) : (
                <>
                  <Link href="/login" className="btn btn-primary">
                    Sign in
                  </Link>
                  <Link href="/register" className="btn btn-secondary">
                    Create account
                  </Link>
                </>
              )}
            </div>

            <div className="eyebrow-grid">
              <div className="eyebrow-card">
                <div className="eyebrow-title">Modules online</div>
                <div className="eyebrow-value">3</div>
              </div>
              <div className="eyebrow-card">
                <div className="eyebrow-title">Live auth path</div>
                <div className="eyebrow-value">FastAPI</div>
              </div>
              <div className="eyebrow-card">
                <div className="eyebrow-title">Testing mode</div>
                <div className="eyebrow-value">Demo bypass</div>
              </div>
              <div className="eyebrow-card">
                <div className="eyebrow-title">UI source</div>
                <div className="eyebrow-value">Wireframes</div>
              </div>
            </div>
          </div>

          <aside className="hero-aside">
            <div className="section-label">Launch tracks</div>
            <div className="surface-list">
              <div className="surface-row">
                <div>
                  <div className="surface-row-title">Homepage</div>
                  <div className="surface-row-meta">Public entry for sign-in, module discovery, and preview routes</div>
                </div>
                <span className="chip chip-primary">Ready</span>
              </div>
              <div className="surface-row">
                <div>
                  <div className="surface-row-title">Admin console</div>
                  <div className="surface-row-meta">Access triage, user visibility, and operational summaries</div>
                </div>
                <span className="chip chip-info">Connected</span>
              </div>
              <div className="surface-row">
                <div>
                  <div className="surface-row-title">Settings</div>
                  <div className="surface-row-meta">Theme, notifications, environment defaults, and key inventory</div>
                </div>
                <span className="chip chip-warning">Local state</span>
              </div>
              <div className="surface-row">
                <div>
                  <div className="surface-row-title">Login</div>
                  <div className="surface-row-meta">Real API login plus bypass buttons for UI testing</div>
                </div>
                <span className="chip chip-success">Ready</span>
              </div>
            </div>
          </aside>
        </section>

        <section style={{ marginBottom: '40px' }}>
          <div className="section-label">What ships first</div>
          <div className="grid-auto">
            <div className="content-card card-body">
              <div className="surface-row-title">Access governance</div>
              <p className="page-subtitle">Users can request access, admins can approve or deny it, and audit-friendly flows already exist.</p>
            </div>
            <div className="content-card card-body">
              <div className="surface-row-title">Module-led navigation</div>
              <p className="page-subtitle">The shell reads enabled modules from the backend and routes users into the right workspace.</p>
            </div>
            <div className="content-card card-body">
              <div className="surface-row-title">Design system portability</div>
              <p className="page-subtitle">Wireframe tokens, layout rules, and theme behavior now live in the app-wide frontend layer.</p>
            </div>
          </div>
        </section>

        <section>
          <div className="section-label">Current delivery scope</div>
          <div className="metric-grid">
            <div className="metric-card">
              <div className="metric-label">Real backend integrations</div>
              <div className="metric-value">Auth</div>
              <div className="metric-meta">Login, registration, /me, admin users, access requests, and DQ module endpoints.</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Preview support</div>
              <div className="metric-value">Demo</div>
              <div className="metric-meta">Admin and analyst bypass modes are available from the login screen for UI walkthroughs.</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Next step</div>
              <div className="metric-value">Modules</div>
              <div className="metric-meta">The same system can now be carried into DQ and the remaining module surfaces.</div>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
