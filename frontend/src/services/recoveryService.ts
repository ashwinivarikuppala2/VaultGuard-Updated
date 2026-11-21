import { api } from './api';
import {
  ApiResponse,
  DestinationType,
  OverwritePolicy,
  RecoveryJob,
  RecoveryPointOption,
  RestorePreviewResponse,
} from '../types';

export interface RestorePreviewParams {
  job_type: string;
  file_version_ids?: string[];
  folder_path?: string;
  device_id?: string;
  point_in_time?: string;
  destination_path?: string;
  destination_type?: DestinationType;
  overwrite_policy?: OverwritePolicy;
}

export interface RestoreSingleParams {
  file_version_id: string;
  destination_path?: string;
  destination_type?: DestinationType;
  overwrite_policy?: OverwritePolicy;
}

export interface RestoreFolderParams {
  folder_path: string;
  device_id?: string;
  destination_path?: string;
  destination_type?: DestinationType;
  overwrite_policy?: OverwritePolicy;
}

export interface RestoreBulkParams {
  file_version_ids: string[];
  destination_path?: string;
  destination_type?: DestinationType;
  overwrite_policy?: OverwritePolicy;
}

export interface RestorePointInTimeParams {
  snapshot_time: string;
  device_id?: string;
  destination_path?: string;
  destination_type?: DestinationType;
  overwrite_policy?: OverwritePolicy;
}

export const recoveryService = {
  previewRestore: async (params: RestorePreviewParams): Promise<RestorePreviewResponse> => {
    const res = await api.post<ApiResponse<RestorePreviewResponse>>('/recovery/preview', params);
    return res.data.data;
  },

  restoreSingle: async (params: RestoreSingleParams): Promise<RecoveryJob> => {
    const res = await api.post<ApiResponse<RecoveryJob>>('/recovery/restore/single', params);
    return res.data.data;
  },

  restoreFolder: async (params: RestoreFolderParams): Promise<RecoveryJob> => {
    const res = await api.post<ApiResponse<RecoveryJob>>('/recovery/restore/folder', params);
    return res.data.data;
  },

  restoreBulk: async (params: RestoreBulkParams): Promise<RecoveryJob> => {
    const res = await api.post<ApiResponse<RecoveryJob>>('/recovery/restore/bulk', params);
    return res.data.data;
  },

  restorePointInTime: async (params: RestorePointInTimeParams): Promise<RecoveryJob> => {
    const res = await api.post<ApiResponse<RecoveryJob>>('/recovery/restore/point-in-time', params);
    return res.data.data;
  },

  listRecoveryJobs: async (params?: {
    status?: string;
    job_type?: string;
    page?: number;
    page_size?: number;
  }): Promise<{ items: RecoveryJob[]; total: number; page: number; page_size: number }> => {
    const res = await api.get<ApiResponse<{ items: RecoveryJob[]; total: number; page: number; page_size: number }>>(
      '/recovery/jobs',
      { params }
    );
    return res.data.data;
  },

  getRecoveryJob: async (jobId: string): Promise<RecoveryJob> => {
    const res = await api.get<ApiResponse<RecoveryJob>>(`/recovery/jobs/${jobId}`);
    return res.data.data;
  },

  downloadRestoredItem: async (jobId: string, itemId: string): Promise<Blob> => {
    const res = await api.get<Blob>(`/recovery/jobs/${jobId}/items/${itemId}/download`, {
      responseType: 'blob',
    });
    return res.data;
  },

  downloadRestoreArchive: async (jobId: string): Promise<Blob> => {
    const res = await api.get<Blob>(`/recovery/jobs/${jobId}/download`, {
      responseType: 'blob',
    });
    return res.data;
  },

  cancelRecoveryJob: async (jobId: string): Promise<RecoveryJob> => {
    const res = await api.post<ApiResponse<RecoveryJob>>(`/recovery/jobs/${jobId}/cancel`);
    return res.data.data;
  },

  retryRecoveryJob: async (jobId: string): Promise<RecoveryJob> => {
    const res = await api.post<ApiResponse<RecoveryJob>>(`/recovery/jobs/${jobId}/retry`);
    return res.data.data;
  },

  getRecoveryPoints: async (deviceId?: string): Promise<RecoveryPointOption[]> => {
    const res = await api.get<ApiResponse<RecoveryPointOption[]>>('/recovery/recovery-points', {
      params: { device_id: deviceId },
    });
    return res.data.data;
  },

  actOnApproval: async (approvalId: string, action: 'APPROVE' | 'REJECT', notes?: string): Promise<any> => {
    const res = await api.post<ApiResponse<any>>(`/recovery/approvals/${approvalId}/action`, {
      action,
      notes,
    });
    return res.data.data;
  },
};

