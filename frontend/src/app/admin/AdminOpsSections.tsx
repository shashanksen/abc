'use client';

/**
 * New admin sections — drop into frontend/src/app/admin/page.tsx
 *
 * Integration:
 *   1. Add the new imports at the top.
 *   2. Add the three new components (AgentOpsSection, ActivityFeedSection)
 *      to the bottom of the existing Admin() return JSX, after the Users
 *      section.
 *   3. The existing summary stats / access requests / users sections stay
 *      unchanged.
 *
 * Visual style: uses your existing classes (section-label, page-header,
 * stat-card, surface-list, surface-row, chip-*, card table-scroll, btn).
 * No new CSS.
 */
import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  adminApi,
  type ActivityItem,
  type AgentTaskItem,
  type AgentUsageRow,
  type KillSwitchState,
} from '@/lib/coreApi';
import { ApiError } from '@/lib/errors';


// ─── Agent operations section ────────────────────────────────────────────────
export function AgentOpsSection() {
  const [killSwitch, setKillSwitch] = useState<KillSwitchState | null>(null);
  const [tasks, setTasks] = useState<AgentTaskItem[]>([]);
  const [usage, setUsage] = useState<AgentUsageRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    adminApi.getKillSwitch().then(setKillSwitch).catch(() => {});
    adminApi.listAgentTasks({ limit: 50 }).then(setTasks).catch(() => {});
    adminApi.agentUsage({ top: 10 }).then(setUsage).catch(() => {});
  };

  useEffect(load, []);

  const toggleKill = async () => {
    if (!killSwitch) return;
    const action = killSwitch.enabled ? 'enable' : 'disable';
    if (!window.confirm(`This will ${action} the agent platform-wide. Continue?`)) return;
    setBusy(true);
    setError(null);
    try {
      const next = await adminApi.setKillSwitch(!killSwitch.enabled);
      setKillSwitch(next);
    } catch (e) {
      setError(e instanceof ApiError ? e.userMessage() : 'Failed to toggle kill-switch');
    } finally {
      setBusy(false);
    }
  };

  const totalToday = usage.reduce((sum, row) => sum + row.total_chars, 0);
  const tasksToday = usage.reduce((sum, row) => sum + row.task_count, 0);
  const failuresToday = usage.reduce((sum, row) => sum + row.failure_count, 0);

  return (
    <section style={{ marginBottom: '40px' }}>
      <div className="page-header" style={{ marginBottom: '16px' }}>
        <div>
          <div className="section-label" style={{ marginBottom: '8px' }}>Agent operations</div>
          <p className="page-subtitle">Daily usage, recent runs, and the platform-wide kill-switch.</p>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Kill-switch + summary stats */}
      <div className="stats-grid" style={{ marginBottom: '24px' }}>
        <div className="stat-card">
          <div className="stat-label">Kill-switch</div>
          <div className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {killSwitch?.enabled
              ? <span className="chip chip-error">Active</span>
              : <span className="chip chip-success">Off</span>}
            <button
              type="button"
              className={`btn btn-sm ${killSwitch?.enabled ? 'btn-primary' : 'btn-danger'}`}
              onClick={toggleKill}
              disabled={busy || !killSwitch}
            >
              {busy ? '...' : killSwitch?.enabled ? 'Allow agent' : 'Disable agent'}
            </button>
          </div>
          <div className="stat-meta">
            {killSwitch?.enabled
              ? 'All agent invocations are blocked.'
              : 'Agent is allowed to run normally.'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Tasks today</div>
          <div className="stat-value">{tasksToday}</div>
          <div className="stat-meta">Total agent invocations across all users.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Output chars today</div>
          <div className="stat-value">{totalToday.toLocaleString()}</div>
          <div className="stat-meta">Sum of LLM output across all users.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Failures today</div>
          <div className="stat-value">{failuresToday}</div>
          <div className="stat-meta">Tasks that ended in state=failed.</div>
        </div>
      </div>

      {/* Top users by usage today */}
      {usage.length > 0 && (
        <>
          <div className="section-label" style={{ marginBottom: '8px' }}>Top users today</div>
          <div className="card table-scroll" style={{ marginBottom: '24px' }}>
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Tasks</th>
                  <th>Output chars</th>
                  <th>Failures</th>
                  <th>Journey</th>
                </tr>
              </thead>
              <tbody>
                {usage.map((row) => (
                  <tr key={row.user_id}>
                    <td>{row.user_email}</td>
                    <td>{row.task_count}</td>
                    <td>{row.total_chars.toLocaleString()}</td>
                    <td>
                      {row.failure_count > 0
                        ? <span className="chip chip-warning">{row.failure_count}</span>
                        : '0'}
                    </td>
                    <td>
                      <Link href={`/admin/users/${row.user_id}/journey`} className="btn btn-secondary btn-sm">
                        View timeline
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Recent agent tasks */}
      <div className="section-label" style={{ marginBottom: '8px' }}>Recent agent runs</div>
      {tasks.length === 0 ? (
        <div className="content-card card-body">
          <p className="muted">No agent runs recorded yet.</p>
        </div>
      ) : (
        <div className="card table-scroll">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>User</th>
                <th>Skill</th>
                <th>State</th>
                <th>Duration</th>
                <th>Output</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.id}>
                  <td>{new Date(task.started_at).toLocaleString()}</td>
                  <td>{task.user_email || task.user_id.slice(0, 8)}</td>
                  <td><span className="mono">{task.skill_id}</span></td>
                  <td><AgentStateBadge state={task.state} /></td>
                  <td>{task.duration_ms != null ? `${task.duration_ms} ms` : '-'}</td>
                  <td>{task.output_chars != null ? `${task.output_chars} ch` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function AgentStateBadge({ state }: { state: string }) {
  const tone =
    state === 'completed' ? 'success' :
    state === 'failed'    ? 'error'   :
    state === 'working'   ? 'info'    :
                            'warning';
  return <span className={`chip chip-${tone}`}>{state}</span>;
}


// ─── Activity feed section ───────────────────────────────────────────────────
export function ActivityFeedSection() {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [nextBefore, setNextBefore] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    adminApi.listActivity({ limit: 50 }).then((res) => {
      setItems(res.items);
      setNextBefore(res.next_before);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const loadMore = async () => {
    if (!nextBefore) return;
    setLoading(true);
    const res = await adminApi.listActivity({ limit: 50, before: nextBefore });
    setItems((prev) => [...prev, ...res.items]);
    setNextBefore(res.next_before);
    setLoading(false);
  };

  return (
    <section>
      <div className="page-header" style={{ marginBottom: '16px' }}>
        <div>
          <div className="section-label" style={{ marginBottom: '8px' }}>Recent activity</div>
          <p className="page-subtitle">
            Unified feed across logins, audit log, and agent runs. Click a user to see their full timeline.
          </p>
        </div>
      </div>

      {items.length === 0 && !loading ? (
        <div className="content-card card-body">
          <p className="muted">No activity yet.</p>
        </div>
      ) : (
        <div className="card table-scroll">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>User</th>
                <th>Source</th>
                <th>Event</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={`${item.when}-${i}`}>
                  <td>{new Date(item.when).toLocaleString()}</td>
                  <td>
                    {item.user_id && item.user_email ? (
                      <Link href={`/admin/users/${item.user_id}/journey`} style={{ color: 'var(--accent-primary)' }}>
                        {item.user_email}
                      </Link>
                    ) : (item.user_email || '-')}
                  </td>
                  <td><SourceBadge source={item.source} /></td>
                  <td>{item.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {nextBefore && (
        <div style={{ marginTop: '16px', textAlign: 'center' }}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={loadMore} disabled={loading}>
            {loading ? 'Loading…' : 'Load older'}
          </button>
        </div>
      )}
    </section>
  );
}

function SourceBadge({ source }: { source: string }) {
  const tone =
    source === 'AGENT'    ? 'primary' :
    source === 'AUDIT'    ? 'info' :
    source === 'ACTIVITY' ? 'neutral' :
                            'neutral';
  return <span className={`chip chip-${tone}`}>{source}</span>;
}
