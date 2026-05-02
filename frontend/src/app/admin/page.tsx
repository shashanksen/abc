'use client';

import { useEffect, useState } from 'react';
import { RouteGuard } from '@/components/RouteGuard';
import { AppShell } from '@/components/AppShell';
import { useAuth } from '@/hooks/useAuth';
import { adminApi, modulesApi, type AccessRequest, type ModuleSummary } from '@/lib/coreApi';
import { getDemoAccessRequests, getDemoAdminUsers, getDemoModuleName, getDemoModules, isDemoUser } from '@/lib/demoData';
import { ApiError } from '@/lib/errors';
import { AgentOpsSection, ActivityFeedSection } from './AdminOpsSections';

export default function AdminPage() {
  return (
    <RouteGuard requireAdmin>
      <AppShell>
        <Admin />
      </AppShell>
    </RouteGuard>
  );
}

interface UserRow {
  id: string;
  email: string;
  full_name: string;
  is_admin: boolean;
  is_active: boolean;
  last_login_at: string | null;
}

function Admin() {
  const { user } = useAuth();
  const demoSession = isDemoUser(user?.id);
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [modules, setModules] = useState<ModuleSummary[]>([]);
  const [filter, setFilter] = useState<'PENDING' | 'APPROVED' | 'DENIED' | 'CANCELLED'>('PENDING');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => {
    if (demoSession) {
      setRequests(getDemoAccessRequests().filter((request) => request.status === filter));
      setUsers(getDemoAdminUsers());
      setModules(getDemoModules());
      setError(null);
      return;
    }

    adminApi.listRequests(filter).then(setRequests).catch((e) =>
      setError(e instanceof ApiError ? e.userMessage() : 'Failed to load requests'));
    adminApi.listUsers().then(setUsers).catch(() => {});
    modulesApi.list().then(setModules).catch(() => {});
  };

  useEffect(load, [filter]);

  const pendingCount = requests.filter((request) => request.status === 'PENDING').length;
  const adminCount = users.filter((currentUser) => currentUser.is_admin).length;
  const activeUsers = users.filter((currentUser) => currentUser.is_active).length;

  const decide = async (id: string, approve: boolean) => {
    setBusy(id);
    setError(null);
    try {
      const note = window.prompt(`${approve ? 'Approve' : 'Deny'} — note (optional):`) || undefined;
      if (approve) await adminApi.approve(id, note);
      else         await adminApi.deny(id, note);
      load();
    } catch (e: any) {
      setError(e instanceof ApiError ? e.userMessage() : 'Action failed');
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Admin console</h1>
          <p className="page-subtitle">Approve access, review users, and manage workspace operations.</p>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="section-label">Operational summary</div>
      <section className="stats-grid" style={{ marginBottom: '40px' }}>
        <div className="stat-card">
          <div className="stat-label">Pending approvals</div>
          <div className="stat-value">{pendingCount}</div>
          <div className="stat-meta">Requests currently waiting for an admin decision.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Users</div>
          <div className="stat-value">{users.length}</div>
          <div className="stat-meta">Accounts returned by the admin user listing API.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Admins</div>
          <div className="stat-value">{adminCount}</div>
          <div className="stat-meta">Accounts with elevated permissions.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active accounts</div>
          <div className="stat-value">{activeUsers}</div>
          <div className="stat-meta">Enabled users visible to {user?.email}.</div>
        </div>
      </section>

      <section style={{ marginBottom: '40px' }}>
        <div className="page-header" style={{ marginBottom: '16px' }}>
          <div>
            <div className="section-label" style={{ marginBottom: '8px' }}>Access requests</div>
            <p className="page-subtitle">Review and action access submissions.</p>
          </div>
          <div className="page-actions">
            <select className="form-select" value={filter} onChange={(e) => setFilter(e.target.value as any)} style={{ width: '160px' }}>
            <option value="PENDING">Pending</option>
            <option value="APPROVED">Approved</option>
            <option value="DENIED">Denied</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
        </div>

        {requests.length === 0 ? (
          <div className="content-card card-body">
            <p className="muted">No {filter.toLowerCase()} requests are available.</p>
          </div>
        ) : (
          <div className="card table-scroll">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Module</th>
                  <th>Justification</th>
                  <th>Created</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((r) => {
                  const user = users.find((u) => u.id === r.user_id);
                  return (
                    <tr key={r.id}>
                      <td>{user ? `${user.full_name} (${user.email})` : r.user_id.slice(0, 8)}</td>
                      <td>{demoSession ? getDemoModuleName(r.module_id) : modules.find((moduleItem) => moduleItem.id === r.module_id)?.name || `${r.module_id.slice(0, 8)}...`}</td>
                      <td>{r.justification || '-'}</td>
                      <td>{new Date(r.created_at).toLocaleString()}</td>
                      <td>
                        {r.status === 'PENDING' ? (
                          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                            <button className="btn btn-primary btn-sm" disabled={busy === r.id} onClick={() => decide(r.id, true)}>
                              Approve
                            </button>
                            <button className="btn btn-danger btn-sm" disabled={busy === r.id} onClick={() => decide(r.id, false)}>
                              Deny
                            </button>
                          </div>
                        ) : (
                          <StatusPill status={r.status} />
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section style={{ marginBottom: '40px' }}>
        <div className="page-header" style={{ marginBottom: '16px' }}>
          <div>
            <div className="section-label" style={{ marginBottom: '8px' }}>Users</div>
            <p className="page-subtitle">Visibility into account status and last login activity.</p>
          </div>
        </div>
        <div className="card table-scroll">
          <table>
            <thead>
              <tr>
                <th>Email</th>
                <th>Full name</th>
                <th>Admin</th>
                <th>Active</th>
                <th>Last login</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.full_name}</td>
                  <td>{u.is_admin ? <span className="chip chip-primary">Admin</span> : <span className="chip chip-neutral">No</span>}</td>
                  <td>{u.is_active ? <span className="chip chip-success">Active</span> : <span className="chip chip-error">Disabled</span>}</td>
                  <td>{u.last_login_at ? new Date(u.last_login_at).toLocaleString() : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* New: agent operations + activity feed */}
      {!demoSession && (
        <>
          <AgentOpsSection />
          <ActivityFeedSection />
        </>
      )}
    </>
  );
}

function StatusPill({ status }: { status: string }) {
  const classes: Record<string, string> = {
    PENDING: 'chip chip-warning',
    APPROVED: 'chip chip-success',
    DENIED: 'chip chip-error',
    CANCELLED: 'chip chip-neutral',
  };

  return <span className={classes[status] || classes.PENDING}>{status}</span>;
}
