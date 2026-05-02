import { BaseApiClient } from './apiClient';

// ─── Module + access shapes (existing) ───────────────────────────────────────
export interface ModuleSummary {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  icon?: string | null;
  is_enabled: boolean;
  sort_order: number;
}

export interface AccessRequest {
  id: string;
  user_id: string;
  module_id: string;
  requested_role_id: string;
  justification?: string | null;
  status: 'PENDING' | 'APPROVED' | 'DENIED' | 'CANCELLED';
  decided_by?: string | null;
  decided_at?: string | null;
  decision_note?: string | null;
  created_at: string;
}

// ─── Admin ops shapes (new) ──────────────────────────────────────────────────
export interface ActivityItem {
  source: 'ACTIVITY' | 'AUDIT' | 'AGENT';
  when: string;
  user_id: string | null;
  user_email: string | null;
  summary: string;
  detail?: Record<string, unknown> | null;
}

export interface ActivityFeedResponse {
  items: ActivityItem[];
  next_before: string | null;
}

export interface UserJourneyResponse {
  user: {
    id: string;
    email: string;
    full_name: string;
    is_admin: boolean;
    is_active: boolean;
    last_login_at: string | null;
  };
  items: ActivityItem[];
}

export interface AgentTaskItem {
  id: string;
  user_id: string;
  user_email: string | null;
  skill_id: string;
  thread_id: string | null;
  state: 'submitted' | 'working' | 'completed' | 'failed';
  duration_ms: number | null;
  output_chars: number | null;
  error: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface AgentUsageRow {
  user_id: string;
  user_email: string;
  task_count: number;
  total_chars: number;
  failure_count: number;
}

export interface KillSwitchState {
  enabled: boolean;
  description: string | null;
  updated_by: string | null;
  updated_at: string;
}

// ─── API clients ─────────────────────────────────────────────────────────────
export class ModulesApi extends BaseApiClient {
  list() { return this.get<ModuleSummary[]>('/modules'); }
  detail(id: string) { return this.get<unknown>(`/modules/${id}`); }
}

export class AccessApi extends BaseApiClient {
  requestAccess(payload: { module_id: string; requested_role_id: string; justification?: string }) {
    return this.post<AccessRequest>('/access/request', payload);
  }
  myRequests() { return this.get<AccessRequest[]>('/access/my-requests'); }
}

export class AdminApi extends BaseApiClient {
  // Existing admin endpoints
  listRequests(status: string = 'PENDING') {
    return this.get<AccessRequest[]>('/admin/access-requests', { query: { status } });
  }
  approve(id: string, note?: string) {
    return this.post<AccessRequest>(`/admin/access-requests/${id}/approve`, { note });
  }
  deny(id: string, note?: string) {
    return this.post<AccessRequest>(`/admin/access-requests/${id}/deny`, { note });
  }
  listUsers() {
    return this.get<Array<{ id: string; email: string; full_name: string;
                            is_admin: boolean; is_active: boolean;
                            last_login_at: string | null }>>('/admin/users');
  }

  // New admin ops endpoints
  listActivity(opts?: { limit?: number; before?: string }) {
    return this.get<ActivityFeedResponse>('/admin/activity', {
      query: { limit: opts?.limit, before: opts?.before },
    });
  }
  userJourney(userId: string, opts?: { limit?: number }) {
    return this.get<UserJourneyResponse>(`/admin/users/${userId}/journey`, {
      query: { limit: opts?.limit },
    });
  }
  listAgentTasks(opts?: { limit?: number; state?: string }) {
    return this.get<AgentTaskItem[]>('/admin/agent/tasks', {
      query: { limit: opts?.limit, state: opts?.state },
    });
  }
  agentUsage(opts?: { top?: number }) {
    return this.get<AgentUsageRow[]>('/admin/agent/usage', {
      query: { top: opts?.top },
    });
  }
  getKillSwitch() {
    return this.get<KillSwitchState>('/admin/agent/kill-switch');
  }
  setKillSwitch(enabled: boolean) {
    return this.post<KillSwitchState>('/admin/agent/kill-switch', { enabled });
  }
}

export const modulesApi = new ModulesApi();
export const accessApi  = new AccessApi();
export const adminApi   = new AdminApi();
