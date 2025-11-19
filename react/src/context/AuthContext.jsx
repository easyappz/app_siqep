import React, { createContext, useContext, useEffect, useState } from 'react';
import { fetchCurrentMember } from '../api/auth';

export const AuthContext = createContext(null);

const TOKEN_STORAGE_KEY = 'memberToken';
const MEMBER_STORAGE_KEY = 'memberData';

const getInitialAuthState = () => {
  if (typeof window === 'undefined') {
    return { token: null, member: null };
  }

  const storedToken = window.localStorage.getItem(TOKEN_STORAGE_KEY);
  const storedMemberRaw = window.localStorage.getItem(MEMBER_STORAGE_KEY);

  let storedMember = null;
  if (storedMemberRaw) {
    try {
      storedMember = JSON.parse(storedMemberRaw);
    } catch (error) {
      console.error('Failed to parse stored member data', error);
      storedMember = null;
    }
  }

  return {
    token: storedToken || null,
    member: storedMember,
  };
};

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(null);
  const [member, setMemberState] = useState(null);
  const [isAuthReady, setIsAuthReady] = useState(false);

  // Initialize auth state from persistent storage once on mount
  useEffect(() => {
    const initial = getInitialAuthState();
    setToken(initial.token);
    setMemberState(initial.member);
    setIsAuthReady(true);
  }, []);

  // Persist token
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

  // Persist member data
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    if (member) {
      window.localStorage.setItem(MEMBER_STORAGE_KEY, JSON.stringify(member));
    } else {
      window.localStorage.removeItem(MEMBER_STORAGE_KEY);
    }
  }, [member]);

  // Optionally refresh current member data when token is present
  useEffect(() => {
    if (!token) {
      return;
    }

    let isCancelled = false;

    const loadCurrentMember = async () => {
      try {
        const currentMember = await fetchCurrentMember();

        if (!isCancelled) {
          setMemberState(currentMember || null);
        }
      } catch (error) {
        console.error('Failed to fetch current member', error);

        if (!isCancelled) {
          setToken(null);
          setMemberState(null);
        }
      }
    };

    loadCurrentMember();

    return () => {
      isCancelled = true;
    };
  }, [token]);

  const login = (newToken, newMember) => {
    setToken(newToken || null);
    setMemberState(newMember || null);
    setIsAuthReady(true);
  };

  const logout = () => {
    setToken(null);
    setMemberState(null);
    setIsAuthReady(true);
  };

  const setMember = (nextMember) => {
    setMemberState(nextMember || null);
  };

  const value = {
    token,
    member,
    // Backward compatibility: expose `user` alias if older code relies on it
    user: member,
    isAuthenticated: Boolean(token),
    isAdmin: Boolean(member && member.is_admin),
    isAuthReady,
    login,
    logout,
    setMember,
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
