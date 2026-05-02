'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { RouteGuard } from '@/components/RouteGuard';
import { AppShell } from '@/components/AppShell';
import { adminApi, type ActivityItem, type UserJourneyResponse } from '@/lib/coreApi';
import { ApiError } from '@/lib/errors';

export default function UserJourneyPage() {
  return (
    <RouteGuard requireAdmin>
      <AppShell>
        <UserJourney />
      </AppShell>
    </RouteGuard>
  );
}

function UserJourney() {
  const params = useParams();
  const userId = String(params.id);
  const [data, setData] = useState<UserJourneyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'ALL' | 'ACTIVITY' | 'AUDIT' | 'AGENT'>('ALL');

  useEffect(() => {
    adminApi.userJourney(userId, { limit: 200 })
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.userMessage() : 'Failed to load journey'));
  }, [userId]);

  if (error) {
    return (
      <>
        <div className="page-header">
          <div>
            <h1 className="page-title">User journey</h1>
            <p className="page-subtitle">{error}</p>
          </div>
          <Link href="/admin" className="btn btn-secondary btn-sm">Back to admin</Link>
        </div>
      </>
    );
  }

  if (!data) {
    return (
      <div className="page-header">
        <div>
          <h1 className="page-title">User journey</h1>
          <p className="page-subtitle">Loading…</p>
        </div>
      </div>
    );
  }

  const filtered = filter === 'ALL' ? data.items : data.items.filter((it) => it.source === filter);
  const counts = {
    ACTIVITY: data.items.filter((it) => it.source === 'ACTIVITY').length,
    AUDIT:    data.items.filter((it) => it.source === 'AUDIT').length,
    AGENT:    data.items.filter((it) => it.source === 'AGENT').length,
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">{data.user.full_name}</h1>
          <p className="page-subtitle">{data.user.email}</p>
        </div>
        <Link href="/admin" className="btn btn-secondary btn-sm">Back to admin</Link>
      </div>

      <div className="section-label">Account</div>
      <section className="stats-grid" style={{ marginBottom: '40px' }}>
        <div className="stat-card">
          <div className="stat-label">Status</div>
          <div className="stat-value" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {data.user.is_active
              ? <span className="chip chip-success">Active</span>
              : <span className="chip chip-error">Disabled</span>}
            {data.user.is_admin && <span className="chip chip-primary">Admin</span>}
          </div>
          <div className="stat-meta">Account state.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Last login</div>
          <div className="stat-value">{data.user.last_login_at
            ? new Date(data.user.last_login_at).toLocaleDateString()
            : '—'}</div>
          <div className="stat-meta">{data.user.last_login_at
            ? new Date(data.user.last_login_at).toLocaleTimeString()
            : 'Never logged in'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Activity events</div>
          <div className="stat-value">{counts.ACTIVITY}</div>
          <div className="stat-meta">Logins, module views.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Audit + agent events</div>
          <div className="stat-value">{counts.AUDIT + counts.AGENT}</div>
          <div className="stat-meta">{counts.AUDIT} audit, {counts.AGENT} agent runs.</div>
        </div>
      </section>

      <div className="page-header" style={{ marginBottom: '16px' }}>
        <div>
          <div className="section-label" style={{ marginBottom: '8px' }}>Timeline</div>
          <p className="page-subtitle">Newest first. Capped at 200 events.</p>
        </div>
        <div className="page-actions">
          <select
            className="form-select"
            value={filter}
            onChange={(e) => setFilter(e.target.value as typeof filter)}
            style={{ width: 160 }}
          >
            <option value="ALL">All sources</option>
            <option value="ACTIVITY">Activity</option>
            <option value="AUDIT">Audit</option>
            <option value="AGENT">Agent</option>
          </select>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="content-card card-body">
          <p className="muted">No events for this filter.</p>
        </div>
      ) : (
        <div className="card table-scroll">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Source</th>
                <th>Event</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item, i) => (
                <TimelineRow key={`${item.when}-${i}`} item={item} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function TimelineRow({ item }: { item: ActivityItem }) {
  const tone =
    item.source === 'AGENT'    ? 'primary' :
    item.source === 'AUDIT'    ? 'info' :
                                 'neutral';
  return (
    <tr>
      <td>{new Date(item.when).toLocaleString()}</td>
      <td><span className={`chip chip-${tone}`}>{item.source}</span></td>
      <td>{item.summary}</td>
      <td className="mono" style={{ fontSize: '0.85em' }}>
        {item.detail ? formatDetail(item.detail) : '-'}
      </td>
    </tr>
  );
}

function formatDetail(detail: Record<string, unknown>): string {
  const entries = Object.entries(detail).filter(([, v]) => v != null && v !== '');
  if (entries.length === 0) return '-';
  return entries.map(([k, v]) => `${k}=${String(v)}`).join(' · ');
}
