import { api } from './api';
import { ApiResponse, AuditLog, PaginatedData } from '../types';

export const auditService = {
  async getRecentLogs(skip = 0, limit = 20): Promise<PaginatedData<AuditLog>> {
    const response = await api.get<ApiResponse<PaginatedData<AuditLog>>>('/audit-logs', {
      params: { skip, limit },
    });
    return response.data.data;
  },
};

