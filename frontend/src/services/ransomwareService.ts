import { api } from './api';
import {
  ApiResponse,
  QuarantineFile,
  RansomwareEvent,
  RansomwareStatusResponse,
  SimulateRansomwareResponse,
  ThreatLog,
} from '../types';

export const ransomwareService = {
  async getStatus(): Promise<RansomwareStatusResponse> {
    const response = await api.get<ApiResponse<RansomwareStatusResponse>>('/ransomware/status');
    return response.data.data;
  },

  async getEvents(limit: number = 50): Promise<RansomwareEvent[]> {
    const response = await api.get<ApiResponse<RansomwareEvent[]>>(`/ransomware/events?limit=${limit}`);
    return response.data.data;
  },

  async getLogs(params?: {
    timeframe?: string;
    severity?: string;
    search?: string;
    limit?: number;
  }): Promise<ThreatLog[]> {
    const query = new URLSearchParams();
    if (params?.timeframe) query.append('timeframe', params.timeframe);
    if (params?.severity) query.append('severity', params.severity);
    if (params?.search) query.append('search', params.search);
    if (params?.limit) query.append('limit', String(params.limit));

    const response = await api.get<ApiResponse<ThreatLog[]>>(`/ransomware/logs?${query.toString()}`);
    return response.data.data;
  },

  async exportLogsCsv(params?: {
    timeframe?: string;
    severity?: string;
    search?: string;
  }): Promise<void> {
    const query = new URLSearchParams();
    if (params?.timeframe) query.append('timeframe', params.timeframe);
    if (params?.severity) query.append('severity', params.severity);
    if (params?.search) query.append('search', params.search);

    const response = await api.get(`/ransomware/logs/export?${query.toString()}`, {
      responseType: 'blob',
    });

    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `vaultguard_threat_logs_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  async getQuarantineFiles(limit: number = 50): Promise<QuarantineFile[]> {
    const response = await api.get<ApiResponse<QuarantineFile[]>>(`/ransomware/quarantine?limit=${limit}`);
    return response.data.data;
  },

  async simulateRansomware(payload?: {
    device_id?: string;
    attack_type?: string;
  }): Promise<SimulateRansomwareResponse> {
    const response = await api.post<ApiResponse<SimulateRansomwareResponse>>(
      '/ransomware/simulate',
      payload || {}
    );
    return response.data.data;
  },

  async quarantineFile(payload: {
    file_path: string;
    reason: string;
    device_id?: string;
  }): Promise<QuarantineFile> {
    const response = await api.post<ApiResponse<QuarantineFile>>('/ransomware/quarantine', payload);
    return response.data.data;
  },

  async restoreQuarantineFile(payload: {
    quarantine_id: string;
    destination?: string;
  }): Promise<QuarantineFile> {
    const response = await api.post<ApiResponse<QuarantineFile>>('/ransomware/restore', payload);
    return response.data.data;
  },

  async deleteQuarantineFile(quarantineId: string): Promise<any> {
    const response = await api.delete<ApiResponse<any>>(`/ransomware/quarantine/${quarantineId}`);
    return response.data.data;
  },

  async resolveAllThreats(): Promise<any> {
    const response = await api.post<ApiResponse<any>>('/ransomware/resolve');
    return response.data.data;
  },
};
