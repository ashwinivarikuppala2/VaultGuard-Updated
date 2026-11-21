import { api } from './api';
import { ApiResponse, StorageStatistics } from '../types';

export const storageService = {
  async getStorageStatistics(): Promise<StorageStatistics> {
    const response = await api.get<ApiResponse<StorageStatistics>>('/storage/statistics');
    return response.data.data;
  },
};

