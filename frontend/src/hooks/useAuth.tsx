'use client';

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';

import { authApi, type User } from '@/lib/authApi';
import { ApiError } from '@/lib/errors';
import { TokenStorage } from '@/lib/tokenStorage';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, full_name: string, password: string) => Promise<void>;
  loginAsDemo: (mode: 'admin' | 'user') => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const demoUser = TokenStorage.getDemoUser();
    if (demoUser) {
      setUser(demoUser);
      setLoading(false);
      return;
    }

    const token = TokenStorage.get();
    if (!token) {
      setLoading(false);
      return;
    }
    authApi.me()
      .then(setUser)
      .catch((e) => {
        if (e instanceof ApiError) TokenStorage.clear();
      })
      .finally(() => setLoading(false));
  }, []);

  const login: AuthContextValue['login'] = async (email, password) => {
    const tok = await authApi.login({ email, password });
    TokenStorage.clearDemoUser();
    TokenStorage.set(tok.access_token);
    const me = await authApi.me();
    setUser(me);
    router.push(me.is_admin ? '/admin' : '/dashboard');
  };

  const register: AuthContextValue['register'] = async (email, full_name, password) => {
    await authApi.register({ email, full_name, password });
    await login(email, password);
  };

  const loginAsDemo: AuthContextValue['loginAsDemo'] = (mode) => {
    TokenStorage.clear();

    const demoUser: User = mode === 'admin'
      ? {
          id: 'demo-admin',
          email: 'admin@demo.local',
          full_name: 'Demo Admin',
          is_admin: true,
          is_active: true,
        }
      : {
          id: 'demo-user',
          email: 'analyst@demo.local',
          full_name: 'Demo Analyst',
          is_admin: false,
          is_active: true,
        };

    TokenStorage.setDemoUser(demoUser);
    setUser(demoUser);
    router.push(demoUser.is_admin ? '/admin' : '/dashboard');
  };

  const logout = () => {
    TokenStorage.clear();
    TokenStorage.clearDemoUser();
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, loginAsDemo, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
