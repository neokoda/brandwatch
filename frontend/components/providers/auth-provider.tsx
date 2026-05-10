"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { getUser, getToken, clearToken, setUser, setToken } from "@/lib/auth";
import { authApi } from "@/lib/api";
import type { AuthUser } from "@/lib/types";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  login: async () => {},
  logout: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const cached = getUser();
    if (cached && getToken()) {
      setUserState(cached);
    }
    setLoading(false);
  }, []);

  async function login(email: string, password: string) {
    const data = await authApi.login(email, password);
    const authUser: AuthUser = {
      user_id: data.user_id,
      email,
      role: data.role,
      account_id: data.account_id,
      account_name: data.account_name,
      account_slug: data.account_slug,
    };
    setToken(data.access_token);
    setUser(authUser);
    setUserState(authUser);
  }

  function logout() {
    clearToken();
    setUserState(null);
    window.location.href = "/login";
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
