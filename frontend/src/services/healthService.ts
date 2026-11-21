import { api } from './api';
import { ApiResponse, SystemHealth } from '../types';

export const healthService = {
  async getSystemHealth(): Promise<SystemHealth> {
    const response = await api.get<ApiResponse<SystemHealth>>('/health');
    return response.data.data;
  },
};

