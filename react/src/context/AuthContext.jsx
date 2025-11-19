import React, { createContext, useContext, useEffect, useState } from 'react';

const AuthContext = createContext(null);

const TOKEN_STORAGE_KEY = 'memberToken';
const USER_STORAGE_KEY = 'memberUser';

const getInitialAuthState = () => {
  if (typeof window === 'undefined') {
    return { token: null, user: null };
  }

  const storedToken = window.localStorage.getItem(TOKEN_STORAGE_KEY);
  const storedUserRaw = window.localStorage.getItem(USER_STORAGE_KEY);

  let storedUser = null;
  if (storedUserRaw) {
    try {
      storedUser = JSON.parse(storedUserRaw);
    } catch {
      storedUser = null;
    }
  }

  return {
    token: storedToken || null,
    user: storedUser,
  };
};

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const initial = getInitialAuthState();
    setToken(initial.token);
    setUser(initial.user);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    if (token) {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  }, [token]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    if (user) {
      window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    } else {
      window.localStorage.removeItem(USER_STORAGE_KEY);
    }
  }, [user]);

  const login = (newToken, newUser) => {
    setToken(newToken || null);
    setUser(newUser || null);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  const value = {
    token,
    user,
    isAuthenticated: Boolean(token),
    isAdmin: Boolean(user && user.is_admin),
    login,
    logout,
    setUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
};
