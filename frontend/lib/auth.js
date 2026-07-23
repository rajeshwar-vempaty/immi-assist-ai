"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clearClientSession, getAuthMe, logout as apiLogout } from "./api";

const AuthContext = createContext(null);

const PUBLIC_PATHS = ["/login"];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const router = useRouter();
  const pathname = usePathname();

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const me = await getAuthMe();
      setUser(me);
      return me;
    } catch (err) {
      setUser(null);
      if (err.status === 401) {
        clearClientSession();
      } else {
        setError(err.message);
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (loading) return;
    const isPublic = PUBLIC_PATHS.some((p) => pathname?.startsWith(p));
    if (!user && !isPublic) {
      router.replace("/login");
    } else if (user && pathname === "/login") {
      router.replace("/");
    }
  }, [user, loading, pathname, router]);

  const signOut = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      clearClientSession();
      setUser(null);
      router.replace("/login");
    }
  }, [router]);

  const value = useMemo(
    () => ({
      user,
      loading,
      error,
      setUser,
      refresh,
      signOut,
      isAuthenticated: !!user,
    }),
    [user, loading, error, refresh, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
