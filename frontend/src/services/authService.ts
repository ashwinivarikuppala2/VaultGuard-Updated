import { api } from './api';
import {
  ApiResponse,
  AuthTokens,
  EmployeeJoinPayload,
  InviteCodeValidationResult,
  OrgAdminRegisterPayload,
  PersonalRegisterPayload,
  User,
} from '../types';

export const authService = {
  async register(data: {
    email: string;
    password: string;
    full_name: string;
    organization_name?: string;
  }): Promise<AuthTokens> {
    const response = await api.post<ApiResponse<AuthTokens>>('/auth/register', data);
    return response.data.data;
  },

  async registerPersonal(data: PersonalRegisterPayload): Promise<AuthTokens> {
    const response = await api.post<ApiResponse<AuthTokens>>('/auth/register/personal', data);
    return response.data.data;
  },

  async registerOrganization(data: OrgAdminRegisterPayload): Promise<AuthTokens> {
    const response = await api.post<ApiResponse<AuthTokens>>('/auth/register/organization', data);
    return response.data.data;
  },

  async validateInviteCode(code: string): Promise<InviteCodeValidationResult> {
    const response = await api.get<ApiResponse<InviteCodeValidationResult>>(`/auth/validate-invite/${encodeURIComponent(code.trim())}`);
    return response.data.data;
  },

  async registerEmployee(data: EmployeeJoinPayload): Promise<AuthTokens> {
    const response = await api.post<ApiResponse<AuthTokens>>('/auth/register/employee', data);
    return response.data.data;
  },

  async login(credentials: { email: string; password: string }): Promise<AuthTokens> {
    const response = await api.post<ApiResponse<AuthTokens>>('/auth/login', credentials);
    return response.data.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<ApiResponse<User>>('/auth/me');
    return response.data.data;
  },

  async logout(refreshToken: string): Promise<void> {
    await api.post('/auth/logout', { refresh_token: refreshToken });
  },
};

