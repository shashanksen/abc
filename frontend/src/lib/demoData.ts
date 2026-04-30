import type { AccessRequest, ModuleSummary } from './coreApi';
import { moduleRegistry } from './moduleRegistry';

interface DemoModuleRole {
  id: string;
  code: string;
  name: string;
  description?: string | null;
}

export interface DemoModuleDetail {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  is_enabled: boolean;
  features: { id: string; name: string; code: string }[];
  roles: DemoModuleRole[];
}

export interface DemoAdminUserRow {
  id: string;
  email: string;
  full_name: string;
  is_admin: boolean;
  is_active: boolean;
  last_login_at: string | null;
}

const demoModules: ModuleSummary[] = moduleRegistry.all().map((moduleItem, index) => ({
  id: `demo-module-${moduleItem.code.toLowerCase()}`,
  code: moduleItem.code,
  name: moduleItem.name,
  description: moduleItem.features.length
    ? `${moduleItem.features.length} workflow surfaces available in demo mode.`
    : `${moduleItem.code} workspace`,
  icon: null,
  is_enabled: true,
  sort_order: moduleItem.features[0] ? index + 1 : index + 1,
}));

const demoUsers: DemoAdminUserRow[] = [
  {
    id: 'demo-admin',
    email: 'admin@demo.local',
    full_name: 'Demo Admin',
    is_admin: true,
    is_active: true,
    last_login_at: '2026-04-27T08:15:00Z',
  },
  {
    id: 'demo-user',
    email: 'analyst@demo.local',
    full_name: 'Demo Analyst',
    is_admin: false,
    is_active: true,
    last_login_at: '2026-04-27T07:45:00Z',
  },
];

const demoAccessRequests: AccessRequest[] = [
  {
    id: 'demo-access-001',
    user_id: 'demo-user',
    module_id: 'demo-module-dq',
    requested_role_id: 'demo-role-dq-editor',
    justification: 'Need to generate and review DQ rule sets for onboarding controls.',
    status: 'APPROVED',
    decided_by: 'demo-admin',
    decided_at: '2026-04-27T08:00:00Z',
    decision_note: 'Approved for DQ workflow walkthrough.',
    created_at: '2026-04-26T14:10:00Z',
  },
  {
    id: 'demo-access-002',
    user_id: 'demo-user',
    module_id: 'demo-module-dq',
    requested_role_id: 'demo-role-dq-admin',
    justification: 'Request elevated access for end-to-end demo of technical rule approvals.',
    status: 'PENDING',
    decided_by: null,
    decided_at: null,
    decision_note: null,
    created_at: '2026-04-27T09:20:00Z',
  },
];

export function isDemoUser(userId?: string | null): boolean {
  return Boolean(userId && userId.startsWith('demo-'));
}

export function getDemoModules(): ModuleSummary[] {
  return demoModules;
}

export function getDemoAccessRequests(userId?: string): AccessRequest[] {
  if (!userId) return demoAccessRequests;
  return demoAccessRequests.filter((request) => request.user_id === userId);
}

export function getDemoAdminUsers(): DemoAdminUserRow[] {
  return demoUsers;
}

export function getDemoModuleOptions(): Array<{ id: string; code: string; name: string }> {
  return demoModules.map(({ id, code, name }) => ({ id, code, name }));
}

export function getDemoModuleDetail(id: string): DemoModuleDetail | null {
  const moduleItem = demoModules.find((item) => item.id === id);
  if (!moduleItem) return null;

  const config = moduleRegistry.get(moduleItem.code);
  if (!config) return null;

  return {
    id: moduleItem.id,
    code: moduleItem.code,
    name: moduleItem.name,
    description: moduleItem.description,
    is_enabled: moduleItem.is_enabled,
    features: config.features.map((feature, index) => ({
      id: `${moduleItem.id}-feature-${index + 1}`,
      code: feature.code,
      name: feature.name,
    })),
    roles: [
      {
        id: `demo-role-${moduleItem.code.toLowerCase()}-viewer`,
        code: 'VIEWER',
        name: `${moduleItem.name} Viewer`,
        description: 'Read-only access to the module.',
      },
      {
        id: `demo-role-${moduleItem.code.toLowerCase()}-editor`,
        code: 'EDITOR',
        name: `${moduleItem.name} Editor`,
        description: 'Can create and update module content.',
      },
      {
        id: `demo-role-${moduleItem.code.toLowerCase()}-admin`,
        code: 'ADMIN',
        name: `${moduleItem.name} Admin`,
        description: 'Can approve workflows and manage the module.',
      },
    ],
  };
}

export function getDemoModuleName(moduleId: string): string {
  return demoModules.find((item) => item.id === moduleId)?.name || moduleId;
}