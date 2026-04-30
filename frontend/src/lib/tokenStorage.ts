/**
 * Token storage. Browser-only — guarded for SSR safety.
 *
 * NOTE: Per Anthropic UI artifact rules localStorage isn't allowed in
 * artifacts, but in real Next.js apps it's fine. For real production
 * consider httpOnly cookies via a backend session.
 */

import type { User } from './authApi';

const KEY = 'cdp.token';
const DEMO_USER_KEY = 'cdp.demo-user';

export const TokenStorage = {
  get(): string | null {
    if (typeof window === 'undefined') return null;
    return window.localStorage.getItem(KEY);
  },
  set(token: string): void {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(KEY, token);
  },
  clear(): void {
    if (typeof window === 'undefined') return;
    window.localStorage.removeItem(KEY);
  },
  getDemoUser(): User | null {
    if (typeof window === 'undefined') return null;

    const stored = window.localStorage.getItem(DEMO_USER_KEY);
    if (!stored) return null;

    try {
      return JSON.parse(stored) as User;
    } catch {
      window.localStorage.removeItem(DEMO_USER_KEY);
      return null;
    }
  },
  setDemoUser(user: User): void {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(DEMO_USER_KEY, JSON.stringify(user));
  },
  clearDemoUser(): void {
    if (typeof window === 'undefined') return;
    window.localStorage.removeItem(DEMO_USER_KEY);
  },
};
