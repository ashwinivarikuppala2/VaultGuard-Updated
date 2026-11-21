import { api } from './api';
import {
  ApiResponse,
  BackupJob,
  BackupSnapshot,
  EmployeeBackupDetails,
  EmployeeBackupSummary,
  FileHistoryItem,
  FileVersion,
  PaginatedData,
  ProtectedFolder,
} from '../types';

export const backupService = {
  async startBackup(
    deviceId: string,
    protectedFolderId?: string,
    jobType: 'FULL' | 'INCREMENTAL' | 'MANUAL' = 'FULL'
  ): Promise<BackupJob> {
    const response = await api.post<ApiResponse<BackupJob>>('/backups/start', {
      device_id: deviceId,
      protected_folder_id: protectedFolderId,
      job_type: jobType,
    });
    return response.data.data;
  },

  async manualBackup(data: {
    device_id: string;
    file_path: string;
    file: File;  // Raw File object — no base64 encoding
    protected_folder_id?: string;
  }): Promise<FileVersion> {
    const formData = new FormData();
    formData.append('device_id', data.device_id);
    formData.append('file_path', data.file_path);
    formData.append('file', data.file);
    if (data.protected_folder_id) {
      formData.append('protected_folder_id', data.protected_folder_id);
    }
    // Let axios set the Content-Type header automatically (with multipart boundary)
    const response = await api.post<ApiResponse<FileVersion>>('/backups/manual', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data.data;
  },

  async listBackups(
    deviceId?: string,
    skip = 0,
    limit = 50,
    ownerScope?: 'mine' | 'employees'
  ): Promise<PaginatedData<BackupSnapshot>> {
    const response = await api.get<ApiResponse<PaginatedData<BackupSnapshot>>>('/backups', {
      params: { device_id: deviceId, owner_scope: ownerScope, skip, limit },
    });
    return response.data.data;
  },

  async listEmployeeBackups(): Promise<EmployeeBackupSummary[]> {
    const response = await api.get<ApiResponse<EmployeeBackupSummary[]>>('/backups/employees');
    return response.data.data;
  },

  async getEmployeeBackupDetails(
    employeeId: string,
    skip = 0,
    limit = 20,
    recoverySkip = 0,
    recoveryLimit = 50
  ): Promise<EmployeeBackupDetails> {
    const response = await api.get<ApiResponse<EmployeeBackupDetails>>(
      `/backups/employees/${employeeId}`,
      {
        params: {
          skip,
          limit,
          recovery_skip: recoverySkip,
          recovery_limit: recoveryLimit,
        },
      }
    );
    return response.data.data;
  },

  async listJobs(
    deviceId?: string,
    status?: string,
    skip = 0,
    limit = 50
  ): Promise<PaginatedData<BackupJob>> {
    const response = await api.get<ApiResponse<PaginatedData<BackupJob>>>('/backups/jobs', {
      params: { device_id: deviceId, status, skip, limit },
    });
    return response.data.data;
  },

  async getFileHistory(fileId: string): Promise<FileHistoryItem> {
    const response = await api.get<ApiResponse<FileHistoryItem>>(`/backups/history/${fileId}`);
    return response.data.data;
  },

  async listProtectedFolders(deviceId?: string): Promise<ProtectedFolder[]> {
    const response = await api.get<ApiResponse<ProtectedFolder[]>>('/protected-folders', {
      params: { device_id: deviceId },
    });
    return response.data.data;
  },

  async createProtectedFolder(data: {
    device_id: string;
    folder_path: string;
    scan_interval_seconds?: number;
    include_patterns?: string;
    exclude_patterns?: string;
  }): Promise<ProtectedFolder> {
    const response = await api.post<ApiResponse<ProtectedFolder>>('/protected-folders', data);
    return response.data.data;
  },

  async deleteProtectedFolder(folderId: string): Promise<void> {
    await api.delete(`/protected-folders/${folderId}`);
  },
};

