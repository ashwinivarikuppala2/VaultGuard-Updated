import { api } from './api';
import { ApiResponse, Device, DeviceStatus, PaginatedData } from '../types';

export const deviceService = {
  async list(status?: DeviceStatus, skip = 0, limit = 50): Promise<PaginatedData<Device>> {
    const response = await api.get<ApiResponse<PaginatedData<Device>>>('/devices', {
      params: { status, skip, limit },
    });
    return response.data.data;
  },

  async getByDeviceId(deviceId: string): Promise<Device> {
    const response = await api.get<ApiResponse<Device>>(`/devices/${deviceId}`);
    return response.data.data;
  },

  async register(data: {
    device_id: string;
    name: string;
    os: string;
  }): Promise<Device> {
    const response = await api.post<ApiResponse<Device>>('/devices', data);
    return response.data.data;
  },

  async update(deviceId: string, data: Partial<Device>): Promise<Device> {
    const response = await api.put<ApiResponse<Device>>(`/devices/${deviceId}`, data);
    return response.data.data;
  },
};

