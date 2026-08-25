import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem("campion_token");
    if (!token) { setLoading(false); return; }
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      localStorage.removeItem("campion_token");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // CRITICAL: If returning from Google OAuth callback, skip the /me check.
    // AuthCallback exchanges the session_id and establishes the session first.
    if (window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }
    loadUser();
  }, [loadUser]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("campion_token", data.token);
    setUser(data.user);
    return data.user;
  };

  const register = async (email, password, preferred_name) => {
    const { data } = await api.post("/auth/register", { email, password, preferred_name });
    localStorage.setItem("campion_token", data.token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    // Revoke server-side first so the token dies even if it leaked into a log or URL.
    // A failed call (offline, deleted account) must never trap the user in a signed-in UI.
    try { await api.post("/auth/logout"); } catch { /* clear locally regardless */ }
    localStorage.removeItem("campion_token");
    setUser(null);
  };

  const refresh = async () => {
    const { data } = await api.get("/auth/me");
    setUser(data);
    return data;
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
