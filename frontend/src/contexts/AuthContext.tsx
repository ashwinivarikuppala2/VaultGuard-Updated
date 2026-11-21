import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  AuthTokens,
  EmployeeJoinPayload,
  OrgAdminRegisterPayload,
  PersonalRegisterPayload,
  User,
} from '../types';
import { authService } from '../services/authService';
import { api } from '../services/api';

export const getDashboardRouteForRole = (role?: any): string => {
  const roleName = typeof role === 'string' ? role : role?.name;
  if (roleName === 'ADMIN') return '/admin/dashboard';
  if (roleName === 'EMPLOYEE') return '/employee/dashboard';
  return '/dashboard'; // INDIVIDUAL
};

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (data: { email: string; password: string; full_name: string; organization_name?: string }) => Promise<User>;
  registerPersonal: (data: PersonalRegisterPayload) => Promise<AuthTokens>;
  registerOrganization: (data: OrgAdminRegisterPayload) => Promise<AuthTokens>;
  registerEmployee: (data: EmployeeJoinPayload) => Promise<AuthTokens>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  getDashboardRoute: () => string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const applyAuthSession = (tokens: AuthTokens) => {
    localStorage.setItem('vaultguard_access_token', tokens.access_token);
    localStorage.setItem('vaultguard_refresh_token', tokens.refresh_token);
    api.defaults.headers.common.Authorization = `Bearer ${tokens.access_token}`;
    setUser(tokens.user);
  };

  const fetchCurrentUser = async () => {
    const token = localStorage.getItem('vaultguard_access_token');
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const userData = await authService.getCurrentUser();
      setUser(userData);
    } catch (err) {
      console.error('Failed to authenticate session:', err);
      localStorage.removeItem('vaultguard_access_token');
      localStorage.removeItem('vaultguard_refresh_token');
      delete api.defaults.headers.common.Authorization;
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentUser();
  }, []);

  const login = async (email: string, password: string): Promise<User> => {
    setIsLoading(true);
    try {
      const tokens = await authService.login({ email, password });
      applyAuthSession(tokens);
      return tokens.user;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: { email: string; password: string; full_name: string; organization_name?: string }): Promise<User> => {
    setIsLoading(true);
    try {
      const tokens = await authService.register(data);
      applyAuthSession(tokens);
      return tokens.user;
    } finally {
      setIsLoading(false);
    }
  };

  const registerPersonal = async (data: PersonalRegisterPayload): Promise<AuthTokens> => {
    setIsLoading(true);
    try {
      const tokens = await authService.registerPersonal(data);
      applyAuthSession(tokens);
      return tokens;
    } finally {
      setIsLoading(false);
    }
  };

  const registerOrganization = async (data: OrgAdminRegisterPayload): Promise<AuthTokens> => {
    setIsLoading(true);
    try {
      const tokens = await authService.registerOrganization(data);
      applyAuthSession(tokens);
      return tokens;
    } finally {
      setIsLoading(false);
    }
  };

  const registerEmployee = async (data: EmployeeJoinPayload): Promise<AuthTokens> => {
    setIsLoading(true);
    try {
      const tokens = await authService.registerEmployee(data);
      applyAuthSession(tokens);
      return tokens;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem('vaultguard_refresh_token');
    try {
      if (refreshToken) {
        await authService.logout(refreshToken);
      }
    } catch (e) {
      console.error('Logout error:', e);
    } finally {
      localStorage.removeItem('vaultguard_access_token');
      localStorage.removeItem('vaultguard_refresh_token');
      delete api.defaults.headers.common.Authorization;
      setUser(null);
      window.location.href = '/login';
    }
  };

  const getDashboardRoute = (): string => {
    return getDashboardRouteForRole(user?.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        registerPersonal,
        registerOrganization,
        registerEmployee,
        logout,
        refreshUser: fetchCurrentUser,
        getDashboardRoute,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
