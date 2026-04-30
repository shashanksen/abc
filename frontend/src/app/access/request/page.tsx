'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { RouteGuard } from '@/components/RouteGuard';
import { AppShell } from '@/components/AppShell';
import { useAuth } from '@/hooks/useAuth';
import { BaseApiClient } from '@/lib/apiClient';
import { accessApi } from '@/lib/coreApi';
import { getDemoModuleDetail, getDemoModuleOptions, isDemoUser } from '@/lib/demoData';
import { ApiError } from '@/lib/errors';

interface ModuleDetail {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  is_enabled: boolean;
  features: { id: string; name: string; code: string }[];
  roles: { id: string; code: string; name: string; description?: string | null }[];
}

class _LocalApi extends BaseApiClient {
  listModules() { return this.get<{ id: string; code: string; name: string }[]>('/modules'); }
  detail(id: string) { return this.get<ModuleDetail>(`/modules/${id}`); }
}
const localApi = new _LocalApi();

export default function RequestAccessPage() {
  return (
    <RouteGuard>
      <AppShell>
        <RequestAccessForm />
      </AppShell>
    </RouteGuard>
  );
}

function RequestAccessForm() {
  const router = useRouter();
  const { user } = useAuth();
  const demoSession = isDemoUser(user?.id);
  const [modules, setModules] = useState<{ id: string; code: string; name: string }[]>([]);
  const [moduleId, setModuleId] = useState<string>('');
  const [detail, setDetail] = useState<ModuleDetail | null>(null);
  const [roleId, setRoleId] = useState<string>('');
  const [justification, setJustification] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (demoSession) {
      setModules(getDemoModuleOptions());
      return;
    }

    // List ALL modules (not just user's) — we need to know what to request
    // The /modules endpoint returns only user's. For an unauth-aware list, you'd
    // add a dedicated endpoint. For now we hit the same one which works for admins,
    // and shows whatever the user already has access to. We'll list everything
    // through detail endpoint by hitting one — but here we just need names.
    localApi.listModules().then(setModules).catch(() => setModules([]));
  }, [demoSession]);

  useEffect(() => {
    if (!moduleId) { setDetail(null); setRoleId(''); return; }
    if (demoSession) {
      const demoDetail = getDemoModuleDetail(moduleId);
      if (!demoDetail) {
        setDetail(null);
        setRoleId('');
        return;
      }
      setDetail(demoDetail);
      setRoleId(demoDetail.roles.find((r) => r.code === 'VIEWER')?.id || demoDetail.roles[0]?.id || '');
      return;
    }

    localApi.detail(moduleId).then((d) => {
      setDetail(d);
      setRoleId(d.roles.find((r) => r.code === 'VIEWER')?.id || d.roles[0]?.id || '');
    }).catch(() => setDetail(null));
  }, [demoSession, moduleId]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null); setSuccess(false);
    if (!moduleId || !roleId) {
      setError('Pick a module and role.');
      return;
    }

    if (demoSession) {
      setSuccess(true);
      setTimeout(() => router.push(user?.is_admin ? '/admin' : '/dashboard'), 1200);
      return;
    }

    setSubmitting(true);
    try {
      await accessApi.requestAccess({
        module_id: moduleId,
        requested_role_id: roleId,
        justification: justification.trim() || undefined,
      });
      setSuccess(true);
      setTimeout(() => router.push('/dashboard'), 1200);
    } catch (e: any) {
      setError(e instanceof ApiError ? e.userMessage() : (e.message || 'Failed to submit request'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <header style={{ marginBottom: '1.25rem' }}>
        <h1 style={{ fontSize: '1.5rem' }}>Request module access</h1>
        <p className="muted small">An admin will approve or deny your request.</p>
      </header>

      <form onSubmit={submit} className="card" style={{ maxWidth: 560 }}>
        <div style={{ marginBottom: '0.75rem' }}>
          <label>Module</label>
          <select value={moduleId} onChange={(e) => setModuleId(e.target.value)} required>
            <option value="">— select —</option>
            {modules.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        </div>

        {detail && detail.roles.length > 0 && (
          <div style={{ marginBottom: '0.75rem' }}>
            <label>Role</label>
            <select value={roleId} onChange={(e) => setRoleId(e.target.value)} required>
              {detail.roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}{r.description ? ` — ${r.description}` : ''}
                </option>
              ))}
            </select>
          </div>
        )}

        <div style={{ marginBottom: '0.75rem' }}>
          <label>Justification (optional)</label>
          <textarea rows={3} value={justification} onChange={(e) => setJustification(e.target.value)} maxLength={2000} />
        </div>

        {error && <div className="error-banner">{error}</div>}
        {success && (
          <div style={{ padding: '0.6rem 0.8rem', background: '#052e1c', color: '#4ade80', borderRadius: 6, fontSize: '0.85rem', margin: '0.75rem 0' }}>
            Request submitted. Redirecting…
          </div>
        )}

        <button type="submit" className="btn" disabled={submitting}>
          {submitting ? 'Submitting…' : 'Submit request'}
        </button>
      </form>
    </>
  );
}
