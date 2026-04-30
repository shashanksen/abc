import { BaseApiClient } from './apiClient';

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_admin: boolean;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
}

export class AuthApi extends BaseApiClient {
  register(data: { email: string; full_name: string; password: string }) {
    return this.post<User>('/auth/register', data, { noAuth: true });
  }

  login(data: { email: string; password: string }) {
    return this.post<TokenResponse>('/auth/login', data, { noAuth: true });
  }

  me() {
    return this.get<User>('/auth/me');
  }
}

export const authApi = new AuthApi();
