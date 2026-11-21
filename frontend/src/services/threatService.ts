import { api } from './api';
import {
  Alert,
  ApiResponse,
  CanaryFile,
  Detection,
  LiveTelemetryEvent,
  PaginatedData,
  QuarantineEvent,
  ThreatAnalytics,
  ThreatRule,
} from '../types';

export const threatService = {
  // Threats & Detections
  getThreats: async (params?: {
    severity?: string;
    status?: string;
    device_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<{ items: Detection[]; total: number; skip: number; limit: number }> => {
    const res = await api.get<ApiResponse<{ items: Detection[]; total: number; skip: number; limit: number }>>(
      '/threats',
      { params }
    );
    return res.data.data;
  },

  getDetections: async (params?: {
    severity?: string;
    status?: string;
    device_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedData<Detection>> => {
    const res = await api.get<ApiResponse<PaginatedData<Detection>>>('/detections', { params });
    return res.data.data;
  },

  getLiveEvents: async (limit: number = 50): Promise<LiveTelemetryEvent[]> => {
    const res = await api.get<ApiResponse<LiveTelemetryEvent[]>>('/threats/live', {
      params: { limit },
    });
    return res.data.data;
  },

  // Quarantine
  quarantineDevice: async (
    deviceId: string,
    reason: string,
    suspectPid?: number
  ): Promise<QuarantineEvent> => {
    const res = await api.post<ApiResponse<QuarantineEvent>>(`/quarantine/${deviceId}`, {
      reason,
      suspect_pid: suspectPid,
    });
    return res.data.data;
  },

  releaseDevice: async (deviceId: string): Promise<QuarantineEvent> => {
    const res = await api.post<ApiResponse<QuarantineEvent>>(`/quarantine/${deviceId}/release`);
    return res.data.data;
  },

  getQuarantineEvents: async (isActive?: boolean): Promise<{ items: QuarantineEvent[]; total: number }> => {
    const res = await api.get<ApiResponse<{ items: QuarantineEvent[]; total: number }>>('/quarantine', {
      params: { is_active: isActive },
    });
    return res.data.data;
  },

  // Alerts
  getAlerts: async (params?: {
    severity?: string;
    status?: string;
    device_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<{ items: Alert[]; total: number }> => {
    const res = await api.get<ApiResponse<{ items: Alert[]; total: number }>>('/alerts', {
      params,
    });
    return res.data.data;
  },

  acknowledgeAlert: async (id: string, notes?: string): Promise<Alert> => {
    const res = await api.post<ApiResponse<Alert>>(`/alerts/${id}/acknowledge`, { notes });
    return res.data.data;
  },

  resolveAlert: async (id: string, notes: string): Promise<Alert> => {
    const res = await api.post<ApiResponse<Alert>>(`/alerts/${id}/resolve`, { notes });
    return res.data.data;
  },

  // Threat Analytics
  getThreatAnalytics: async (): Promise<ThreatAnalytics> => {
    const res = await api.get<ApiResponse<ThreatAnalytics>>('/threats/threat-analytics');
    return res.data.data;
  },

  // Threat Rules
  getThreatRules: async (): Promise<ThreatRule[]> => {
    const res = await api.get<ApiResponse<ThreatRule[]>>('/threats/threat-rules');
    return res.data.data;
  },

  createThreatRule: async (data: {
    name: string;
    description: string;
    rule_type: string;
    condition: string;
    threshold: number;
    weight: number;
    severity: string;
    action: string;
    is_enabled: boolean;
  }): Promise<ThreatRule> => {
    const res = await api.post<ApiResponse<ThreatRule>>('/threats/threat-rules', data);
    return res.data.data;
  },

  // Canary Decoys
  deployCanary: async (deviceId: string, folderPath: string): Promise<CanaryFile> => {
    const res = await api.post<ApiResponse<CanaryFile>>('/canary/deploy', {
      device_id: deviceId,
      folder_path: folderPath,
    });
    return res.data.data;
  },

  getCanaries: async (): Promise<CanaryFile[]> => {
    const res = await api.get<ApiResponse<CanaryFile[]>>('/canary');
    return res.data.data;
  },
};

