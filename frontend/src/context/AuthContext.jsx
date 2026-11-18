import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { setAuthFailureHandler } from "../api/client.js";
import { fetchCurrentUser, loginUser, registerUser } from "../api/auth.api.js";
import { tokenStorage } from "../utils/tokenStorage.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);

  const clearAuthState = useCallback(() => {
    tokenStorage.clearTokens();
    setUser(null);
  }, []);

  useEffect(() => {
    setAuthFailureHandler(() => {
      setUser(null);
    });

    let isMounted = true;

    async function restoreSession() {
      if (!tokenStorage.hasTokens()) {
        if (isMounted) {
          setIsInitializing(false);
        }
        return;
      }

      try {
        const currentUser = await fetchCurrentUser();
        if (isMounted) {
          setUser(currentUser);
        }
      } catch {
        tokenStorage.clearTokens();
        if (isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsInitializing(false);
        }
      }
    }

    restoreSession();

    return () => {
      isMounted = false;
      setAuthFailureHandler(null);
    };
  }, []);

  const login = useCallback(async ({ username, password }) => {
    const data = await loginUser({ username, password });
    if (data?.tokens) {
      tokenStorage.setTokens(data.tokens);
    }
    setUser(data?.user || null);
    return data;
  }, []);

  const register = useCallback(async (payload) => {
    const data = await registerUser(payload);
    if (data?.tokens) {
      tokenStorage.setTokens(data.tokens);
    }
    setUser(data?.user || null);
    return data;
  }, []);

  const logout = useCallback(() => {
    clearAuthState();
  }, [clearAuthState]);

  const refreshUser = useCallback(async () => {
    const currentUser = await fetchCurrentUser();
    setUser(currentUser);
    return currentUser;
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isInitializing,
      isInitialized: !isInitializing,
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, isInitializing, login, register, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
