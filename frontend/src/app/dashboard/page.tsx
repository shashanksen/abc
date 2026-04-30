'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { RouteGuard } from '@/components/RouteGuard';
import { AppShell } from '@/components/AppShell';
import { useAuth } from '@/hooks/useAuth';
import { modulesApi, type ModuleSummary, accessApi, type AccessRequest } from '@/lib/coreApi';
import { getDemoAccessRequests, getDemoModules, isDemoUser } from '@/lib/demoData';
import { moduleRegistry } from '@/lib/moduleRegistry';

export default function DashboardPage() {
  return (
    <RouteGuard>
      <AppShell>
        <Dashboard />
      </AppShell>
    </RouteGuard>
  );
}

function Dashboard() {
  const { user } = useAuth();
  const demoSession = isDemoUser(user?.id);
  const [modules, setModules] = useState<ModuleSummary[]>([]);
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [apiHealthy, setApiHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    if (demoSession) {
      setModules(getDemoModules());
      setRequests(getDemoAccessRequests(user?.id));
      setApiHealthy(true);
      return;
    }

    modulesApi.list().then(setModules).catch(() => setModules([]));
    accessApi.myRequests().then(setRequests).catch(() => setRequests([]));
    fetch('/api/health', { cache: 'no-store' })
      .then((res) => setApiHealthy(res.ok))
      .catch(() => setApiHealthy(false));
  }, [demoSession, user?.id]);

  const pendingRequests = requests.filter((request) => request.status === 'PENDING').length;
  const approvedRequests = requests.filter((request) => request.status === 'APPROVED').length;

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Workspace overview for {user?.full_name}</p>
        </div>
      </div>

      <div className="section-label">Key metrics</div>
      <section className="stats-grid" style={{ marginBottom: '40px' }}>
        <div className="stat-card">
          <div className="stat-label">Modules</div>
          <div className="stat-value">{modules.length}</div>
          <div className="stat-meta">Enabled workspaces assigned to your account.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Pending requests</div>
          <div className="stat-value">{pendingRequests}</div>
          <div className="stat-meta">Requests awaiting an admin decision.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Approved access</div>
          <div className="stat-value">{approvedRequests}</div>
          <div className="stat-meta">Approved requests visible in your recent history.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">API health</div>
          <div className="stat-value">{apiHealthy === null ? '--' : apiHealthy ? 'OK' : 'Down'}</div>
          <div className="stat-meta">Live result from the backend health endpoint.</div>
        </div>
      </section>

      <div className="panel-grid" style={{ marginBottom: '40px' }}>
        <section className="content-card card-body">
          <div className="section-label">Assigned modules</div>
          {modules.length === 0 ? (
            <div className="alert alert-warning">No modules are assigned yet. Use the access request flow to unlock one.</div>
          ) : (
            <div className="surface-list">
              {modules.map((moduleItem) => (
                <div key={moduleItem.id} className="surface-row">
                  <div>
                    <div className="surface-row-title">{moduleItem.name}</div>
                    <div className="surface-row-meta">{moduleItem.description || `${moduleItem.code} workspace`}</div>
                  </div>
                  <div className="page-actions">
                    <span className="chip chip-success">Enabled</span>
                    {moduleRegistry.get(moduleItem.code) ? (
                      <Link href={moduleRegistry.get(moduleItem.code)!.basePath} className="btn btn-secondary btn-sm">
                        Open
                      </Link>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="content-card card-body">
          <div className="section-label">Workspace status</div>
          <div className="surface-list">
            <div className="surface-row">
              <div>
                <div className="surface-row-title">Authentication</div>
                <div className="surface-row-meta">Current identity loaded in the client session.</div>
              </div>
              <span className={`chip ${user?.is_admin ? 'chip-primary' : 'chip-info'}`}>{user?.is_admin ? 'Admin' : 'User'}</span>
            </div>
            <div className="surface-row">
              <div>
                <div className="surface-row-title">Health endpoint</div>
                <div className="surface-row-meta">Checks whether the API process is reachable through Next rewrites.</div>
              </div>
              <span className={`chip ${apiHealthy ? 'chip-success' : 'chip-warning'}`}>{apiHealthy === false ? 'Needs review' : 'Operational'}</span>
            </div>
            <div className="surface-row">
              <div>
                <div className="surface-row-title">Recent requests</div>
                <div className="surface-row-meta">The access history feed is backed by the authenticated access API.</div>
              </div>
              <span className="chip chip-neutral">{requests.length} total</span>
            </div>
          </div>
        </section>
      </div>

      <section>
        <div className="section-label">Recent access activity</div>
        {requests.length === 0 ? (
          <div className="content-card card-body">
            <p className="muted">No access requests have been recorded for this user yet.</p>
          </div>
        ) : (
          <div className="card table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Module</th>
                  <th>Status</th>
                  <th>Decision note</th>
                  <th>Requested</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((request) => (
                  <tr key={request.id}>
                    <td>{modules.find((moduleItem) => moduleItem.id === request.module_id)?.name || request.module_id}</td>
                    <td><StatusPill status={request.status} /></td>
                    <td>{request.decision_note || '-'}</td>
                    <td>{new Date(request.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

function StatusPill({ status }: { status: string }) {
  const classNames: Record<string, string> = {
    PENDING: 'chip chip-warning',
    APPROVED: 'chip chip-success',
    DENIED: 'chip chip-error',
    CANCELLED: 'chip chip-neutral',
  };
  return <span className={classNames[status] || classNames.PENDING}>{status}</span>;
}
