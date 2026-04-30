import { ApiError, type ApiErrorPayload } from './errors';
import { TokenStorage } from './tokenStorage';

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

export interface RequestOptions {
  query?: Record<string, string | number | boolean | undefined>;
  body?: unknown;
  signal?: AbortSignal;
  noAuth?: boolean;
}

export class BaseApiClient {
  protected basePath: string;

  constructor(basePath: string = '/api') {
    this.basePath = basePath;
  }

  protected async request<T>(
    method: HttpMethod,
    path: string,
    opts: RequestOptions = {},
  ): Promise<T> {
    const url = this.buildUrl(path, opts.query);
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
    if (!opts.noAuth) {
      const token = TokenStorage.get();
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }

    const init: RequestInit = {
      method,
      headers,
      signal: opts.signal,
      cache: 'no-store',
    };
    if (opts.body !== undefined) {
      init.body = JSON.stringify(opts.body);
    }

    const res = await fetch(url, init);

    // 204 No Content
    if (res.status === 204) return undefined as T;

    const text = await res.text();
    let parsed: unknown = null;
    try { parsed = text ? JSON.parse(text) : null; } catch { parsed = text; }

    if (!res.ok) {
      const errPayload = (parsed as { error?: ApiErrorPayload })?.error
        ?? { code: 'CDP-SYS-0091', message: 'Unknown error', detail: text };
      const apiError = new ApiError(res.status, errPayload);

      // Auto-logout on session expiry
      if (this.isSessionExpired(apiError)) {
        TokenStorage.clear();
        if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
          window.location.href = '/login?expired=1';
        }
      }
      throw apiError;
    }
    return parsed as T;
  }

  private isSessionExpired(err: ApiError): boolean {
    return err.code === 'CDP-AUT-0002' || err.code === 'CDP-AUT-0003' || err.code === 'CDP-AUT-0006';
  }

  protected get<T>(path: string, opts?: RequestOptions)    { return this.request<T>('GET',    path, opts); }
  protected post<T>(path: string, body?: unknown, opts?: RequestOptions) {
    return this.request<T>('POST', path, { ...opts, body });
  }
  protected patch<T>(path: string, body?: unknown, opts?: RequestOptions) {
    return this.request<T>('PATCH', path, { ...opts, body });
  }
  protected del<T>(path: string, opts?: RequestOptions)    { return this.request<T>('DELETE', path, opts); }

  private buildUrl(path: string, query?: Record<string, unknown>): string {
    const full = path.startsWith('/') ? `${this.basePath}${path}` : `${this.basePath}/${path}`;
    if (!query) return full;
    const qs = Object.entries(query)
      .filter(([, v]) => v !== undefined && v !== null)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
      .join('&');
    return qs ? `${full}?${qs}` : full;
  }
}