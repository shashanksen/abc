'use client';

import { useEffect, useState } from 'react';
import { AppShell } from '@/components/AppShell';
import { RouteGuard } from '@/components/RouteGuard';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/hooks/useTheme';

interface SettingsState {
  fullName: string;
  email: string;
  role: string;
  compactView: boolean;
  showTimestamps: boolean;
  pipelineFailures: boolean;
  serviceAlerts: boolean;
  uploadCompletion: boolean;
  defaultPageSize: string;
  sessionTimeout: string;
}

export default function SettingsPage() {
  return (
    <RouteGuard>
      <AppShell>
        <SettingsView />
      </AppShell>
    </RouteGuard>
  );
}

function SettingsView() {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [saved, setSaved] = useState(false);
  const [settings, setSettings] = useState<SettingsState>({
    fullName: '',
    email: '',
    role: 'Viewer',
    compactView: false,
    showTimestamps: true,
    pipelineFailures: true,
    serviceAlerts: true,
    uploadCompletion: false,
    defaultPageSize: '50',
    sessionTimeout: '30',
  });

  useEffect(() => {
    if (!user) return;

    setSettings((current) => ({
      ...current,
      fullName: user.full_name,
      email: user.email,
      role: user.is_admin ? 'Administrator' : 'User',
    }));
  }, [user]);

  const update = <K extends keyof SettingsState>(key: K, value: SettingsState[K]) => {
    setSaved(false);
    setSettings((current) => ({ ...current, [key]: value }));
  };

  const save = () => {
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1800);
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Account preferences and local workspace configuration.</p>
        </div>
      </div>

      {saved && <div className="alert alert-success">Settings saved locally for this browser session.</div>}

      <section style={{ marginBottom: '40px' }}>
        <div className="section-label">Profile</div>
        <div className="settings-card card-body">
          <div className="form-group">
            <label className="form-label">Display name</label>
            <input className="form-input" value={settings.fullName} onChange={(e) => update('fullName', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input className="form-input" value={settings.email} onChange={(e) => update('email', e.target.value)} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Role</label>
            <select className="form-select" value={settings.role} onChange={(e) => update('role', e.target.value)}>
              <option>Administrator</option>
              <option>User</option>
              <option>Viewer</option>
            </select>
          </div>
        </div>
      </section>

      <section style={{ marginBottom: '40px' }}>
        <div className="section-label">Appearance</div>
        <div className="settings-card card-body">
          <ToggleRow
            title="Dark mode"
            description="Switch the workspace theme."
            checked={theme === 'dark'}
            onToggle={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          />
          <ToggleRow
            title="Compact view"
            description="Reduce spacing in dense tables and lists."
            checked={settings.compactView}
            onToggle={() => update('compactView', !settings.compactView)}
          />
          <ToggleRow
            title="Show timestamps"
            description="Prefer exact timestamps over relative time labels."
            checked={settings.showTimestamps}
            onToggle={() => update('showTimestamps', !settings.showTimestamps)}
          />
        </div>
      </section>

      <section style={{ marginBottom: '40px' }}>
        <div className="section-label">Notifications</div>
        <div className="settings-card card-body">
          <ToggleRow
            title="Pipeline failures"
            description="Show alerts for failed jobs and orchestration issues."
            checked={settings.pipelineFailures}
            onToggle={() => update('pipelineFailures', !settings.pipelineFailures)}
          />
          <ToggleRow
            title="Service alerts"
            description="Keep environment degradation visible in the UI."
            checked={settings.serviceAlerts}
            onToggle={() => update('serviceAlerts', !settings.serviceAlerts)}
          />
          <ToggleRow
            title="Upload completion"
            description="Surface completion messages after import flows finish."
            checked={settings.uploadCompletion}
            onToggle={() => update('uploadCompletion', !settings.uploadCompletion)}
          />
        </div>
      </section>

      <section style={{ marginBottom: '40px' }}>
        <div className="section-label">System configuration</div>
        <div className="settings-card card-body">
          <div className="form-group">
            <label className="form-label">API base</label>
            <input className="form-input mono" value={process.env.NEXT_PUBLIC_API_BASE || '/api'} readOnly />
          </div>
          <div className="panel-grid" style={{ gridTemplateColumns: '220px 220px' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Default page size</label>
              <select className="form-select" value={settings.defaultPageSize} onChange={(e) => update('defaultPageSize', e.target.value)}>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Session timeout (minutes)</label>
              <input className="form-input" type="number" value={settings.sessionTimeout} onChange={(e) => update('sessionTimeout', e.target.value)} />
            </div>
          </div>
        </div>
      </section>

      <section style={{ marginBottom: '40px' }}>
        <div className="section-label">API keys</div>
        <div className="settings-card card-body">
          <div className="surface-list">
            <div className="surface-row">
              <div>
                <div className="surface-row-title">Production</div>
                <div className="surface-row-meta mono">sk_prod_****************************3f8a</div>
              </div>
              <span className="chip chip-neutral">Created Jan 15</span>
            </div>
            <div className="surface-row">
              <div>
                <div className="surface-row-title">Development</div>
                <div className="surface-row-meta mono">sk_dev_*****************************9c2b</div>
              </div>
              <span className="chip chip-neutral">Created Feb 01</span>
            </div>
          </div>
          <div style={{ marginTop: '16px' }}>
            <button type="button" className="btn btn-secondary btn-sm">Generate new key</button>
          </div>
        </div>
      </section>

      <section>
        <div className="section-label">Danger zone</div>
        <div className="danger-zone">
          <div className="surface-row-title" style={{ color: 'var(--status-error)' }}>Delete account data</div>
          <p className="page-subtitle" style={{ marginTop: '8px', marginBottom: '16px' }}>
            This is a UI stub for now. The backend delete workflow is not wired into this screen.
          </p>
          <button type="button" className="btn btn-danger btn-sm">Delete all data</button>
        </div>
      </section>

      <div className="save-bar">
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => window.location.reload()}>
          Reset
        </button>
        <button type="button" className="btn btn-primary btn-sm" onClick={save}>
          Save changes
        </button>
      </div>
    </>
  );
}

function ToggleRow({
  title,
  description,
  checked,
  onToggle,
}: {
  title: string;
  description: string;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="surface-row">
      <div>
        <div className="surface-row-title">{title}</div>
        <div className="surface-row-meta">{description}</div>
      </div>
      <button type="button" className={`btn btn-sm ${checked ? 'btn-primary' : 'btn-secondary'}`} onClick={onToggle}>
        {checked ? 'On' : 'Off'}
      </button>
    </div>
  );
}