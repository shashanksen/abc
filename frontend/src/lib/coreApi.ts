import { BaseApiClient } from './apiClient';

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
}

export const modulesApi = new ModulesApi();
export const accessApi  = new AccessApi();
export const adminApi   = new AdminApi();
