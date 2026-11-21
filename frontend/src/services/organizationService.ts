import { api } from './api';
import { ApiResponse, Organization, PaginatedData, User } from '../types';

export const organizationService = {
  async list(skip = 0, limit = 50): Promise<PaginatedData<Organization>> {
    const response = await api.get<ApiResponse<PaginatedData<Organization>>>('/organizations', {
      params: { skip, limit },
    });
    return response.data.data;
  },

  async getById(id: string): Promise<Organization> {
    const response = await api.get<ApiResponse<Organization>>(`/organizations/${id}`);
    return response.data.data;
  },

  async create(data: {
    name: string;
    contact_email: string;
    slug?: string;
    max_devices?: number;
    storage_quota_bytes?: number;
  }): Promise<Organization> {
    const response = await api.post<ApiResponse<Organization>>('/organizations', data);
    return response.data.data;
  },

  async update(id: string, data: Partial<Organization>): Promise<Organization> {
    const response = await api.put<ApiResponse<Organization>>(`/organizations/${id}`, data);
    return response.data.data;
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/organizations/${id}`);
  },

  async getInviteCode(): Promise<{ invite_code: string; organization_name: string }> {
    const response = await api.get<ApiResponse<{ invite_code: string; organization_name: string }>>('/organizations/invite-code');
    return response.data.data;
  },

  async regenerateInviteCode(): Promise<{ invite_code: string; organization_name: string }> {
    const response = await api.post<ApiResponse<{ invite_code: string; organization_name: string }>>('/organizations/invite-code/regenerate');
    return response.data.data;
  },

  async generateInviteCode(): Promise<{ invite_code: string; organization_name: string }> {
    const response = await api.post<ApiResponse<{ invite_code: string; organization_name: string }>>('/organizations/invite-code/generate');
    return response.data.data;
  },

  async listEmployees(): Promise<User[]> {
    const response = await api.get<ApiResponse<User[]>>('/organizations/employees');
    return response.data.data;
  },
};

