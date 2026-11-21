export type RoleType = 'ADMIN' | 'EMPLOYEE' | 'INDIVIDUAL';

export type DeviceStatus = 'ONLINE' | 'OFFLINE' | 'REVOKED' | 'PENDING' | 'QUARANTINED';

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error: {
    code: string;
    message: string;
    details?: any;
  } | null;
  timestamp: string;
  trace_id?: string;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface Role {
  id: string;
  name: RoleType;
  description?: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  organization_id?: string | null;
  role: Role;
  is_active: boolean;
  is_verified: boolean;
  last_login_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
  invite_code?: string | null;
  organization_name?: string | null;
}

export interface PersonalRegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface OrgAdminRegisterPayload {
  organization_name: string;
  email: string;
  password: string;
  full_name: string;
  storage_quota_bytes?: number;
  max_devices?: number;
}

export interface EmployeeJoinPayload {
  invite_code: string;
  email: string;
  password: string;
  full_name: string;
}

export interface InviteCodeValidationResult {
  is_valid: boolean;
  organization_name?: string | null;
  organization_slug?: string | null;
  message?: string | null;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  invite_code?: string;
  contact_email: string;
  max_devices: number;
  storage_quota_bytes: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Device {
  id: string;
  device_id: string;
  name: string;
  os: string;
  status: DeviceStatus;
  last_seen?: string | null;
  organization_id?: string | null;
  user_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: string;
  organization_id?: string | null;
  user_id?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  details?: Record<string, any> | null;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
}

export interface ServiceComponentHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
  latency_ms?: number | null;
  details?: string | null;
}

export interface SystemHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
  timestamp: string;
  version: string;
  environment: string;
  services: {
    database: ServiceComponentHealth;
    redis: ServiceComponentHealth;
    minio: ServiceComponentHealth;
  };
}

// Module 2 - Secure Backup Engine Types
export type BackupJobStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'PARTIAL' | 'FAILED';

export interface BackupJob {
  id: string;
  organization_id: string;
  device_id: string;
  job_type: 'FULL' | 'INCREMENTAL' | 'MANUAL';
  status: BackupJobStatus;
  started_at?: string | null;
  completed_at?: string | null;
  total_files: number;
  bytes_processed: number;
  files_failed: number;
  files_skipped: number;
  duration_seconds: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProtectedFolder {
  id: string;
  organization_id: string;
  device_id: string;
  folder_path: string;
  is_active: boolean;
  scan_interval_seconds: number;
  include_patterns: string;
  exclude_patterns: string;
  created_at: string;
  updated_at: string;
}

export interface FileVersion {
  id: string;
  file_id: string;
  version_number: number;
  storage_path: string;
  file_hash_sha256: string;
  size_bytes: number;
  original_size_bytes: number;
  compressed_size_bytes: number;
  compression_algorithm: string;
  encryption_algorithm: string;
  is_encrypted: boolean;
  created_at: string;
}

export interface FileHistoryItem {
  id: string;
  file_path: string;
  original_filename: string;
  file_size: number;
  total_versions: number;
  is_deleted: boolean;
  versions: FileVersion[];
  created_at: string;
  updated_at: string;
}

export interface BackupSnapshot {
  version_id: string;
  file_id: string;
  file_path: string;
  original_filename: string;
  version_number: number;
  file_hash_sha256: string;
  original_size_bytes: number;
  encrypted_size_bytes: number;
  storage_path: string;
  created_at: string;
}

export interface EmployeeBackupSummary {
  employee_id: string;
  full_name: string;
  email: string;
  is_active: boolean;
  created_at: string;
  total_backup_files: number;
  storage_used_bytes: number;
  last_backup_at?: string | null;
  backup_status: string;
}

export interface EmployeeBackupVersion {
  id: string;
  version_number: number;
  original_size_bytes: number;
  encrypted_size_bytes: number;
  file_hash_sha256: string;
  is_encrypted: boolean;
  encryption_algorithm: string;
  created_at: string;
}

export interface EmployeeBackupFile {
  id: string;
  file_path: string;
  original_filename: string;
  file_size: number;
  total_versions: number;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  versions: EmployeeBackupVersion[];
}

export interface EmployeeRecoveryHistoryItem {
  id: string;
  job_type: string;
  status: string;
  total_files: number;
  files_restored: number;
  files_failed: number;
  bytes_restored: number;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface EmployeeBackupDetails {
  employee: User;
  total_backup_files: number;
  storage_used_bytes: number;
  last_backup_at?: string | null;
  backup_status: string;
  files: PaginatedData<EmployeeBackupFile>;
  recovery_history: PaginatedData<EmployeeRecoveryHistoryItem>;
}

export interface DeviceStorageUsage {
  device_id: string;
  device_name: string;
  total_files: number;
  total_versions: number;
  total_bytes: number;
}

export interface StorageStatistics {
  total_files: number;
  total_versions: number;
  total_original_bytes: number;
  total_stored_bytes: number;
  space_saved_bytes: number;
  compression_savings_percent: number;
  active_protected_folders: number;
  total_backup_jobs: number;
  successful_backup_jobs: number;
  failed_backup_jobs: number;
  device_breakdown: DeviceStorageUsage[];
}

export interface BackupPolicy {
  id: string;
  name: string;
  schedule_type: 'CONTINUOUS' | 'HOURLY' | 'DAILY' | 'WEEKLY';
  retention_days: number;
  compression_level: number;
  encryption_standard: 'AES-256-GCM';
  is_active: boolean;
}

// Module 3 - Threat Detection, Monitoring, Alerts & Quarantine Types
export type ThreatSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AlertStatus = 'NEW' | 'ACKNOWLEDGED' | 'RESOLVED' | 'DISMISSED';

export interface Detection {
  id: string;
  organization_id: string;
  device_id: string;
  detection_type: string;
  threat_name: string;
  severity: ThreatSeverity;
  risk_score: number;
  confidence_score: number;
  status: string;
  details?: Record<string, any> | null;
  is_resolved: boolean;
  created_at: string;
  resolved_at?: string | null;
}

export interface LiveTelemetryEvent {
  id: string;
  device_id: string;
  event_type: string;
  file_path: string;
  risk_score: number;
  risk_level: ThreatSeverity;
  entropy_score: number;
  write_rate: number;
  rename_rate: number;
  canary_hit: boolean;
  created_at: string;
}

export interface Alert {
  id: string;
  organization_id: string;
  device_id?: string | null;
  detection_id?: string | null;
  title: string;
  description: string;
  severity: ThreatSeverity;
  status: AlertStatus;
  acknowledged_by_id?: string | null;
  acknowledged_at?: string | null;
  resolved_by_id?: string | null;
  resolved_at?: string | null;
  mitigation_notes?: string | null;
  created_at: string;
}

export interface QuarantineEvent {
  id: string;
  organization_id: string;
  device_id?: string | null;
  reason: string;
  isolation_level: string;
  is_active: boolean;
  quarantined_by_id?: string | null;
  created_at: string;
  restored_at?: string | null;
  restored_by_id?: string | null;
}

export interface ThreatRule {
  id: string;
  organization_id?: string | null;
  name: string;
  description: string;
  rule_type: string;
  condition: string;
  threshold: number;
  weight: number;
  severity: ThreatSeverity;
  action: string;
  is_enabled: boolean;
  created_at: string;
}

export interface CanaryFile {
  id: string;
  device_id: string;
  file_path: string;
  filename: string;
  canary_token: string;
  is_tampered: boolean;
  last_checked_at?: string | null;
  created_at: string;
}

export interface ThreatAnalytics {
  total_detections: number;
  active_detections: number;
  quarantined_endpoints: number;
  canaries_deployed: number;
  canaries_tripped: number;
  fleet_average_risk_score: number;
  alerts_by_severity: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  threat_distribution: Array<{ name: string; count: number }>;
  timeline: Array<{ date: string; detections: number }>;
}

// ==================== Module 4: Recovery, Restoration & Integrity ====================

export type RecoveryJobType = 'SINGLE_FILE' | 'FOLDER' | 'BULK' | 'POINT_IN_TIME';
export type RecoveryJobStatus = 'PENDING' | 'IN_PROGRESS' | 'VERIFYING' | 'COMPLETED' | 'PARTIAL' | 'FAILED' | 'CANCELLED';
export type RecoveryItemStatus = 'PENDING' | 'IN_PROGRESS' | 'VERIFYING' | 'COMPLETED' | 'SKIPPED' | 'FAILED' | 'CANCELLED';
export type OverwritePolicy = 'SKIP' | 'RENAME' | 'OVERWRITE';
export type DestinationType = 'SAFE_DIR' | 'ORIGINAL' | 'CUSTOM_SAFE_DIR';
export type ThreatRiskLabel = 'no known threat detected' | 'potentially suspicious' | 'not enough information';

export interface RecoveryJobItem {
  id: string;
  recovery_job_id: string;
  file_id: string;
  file_version_id: string;
  original_path: string;
  target_path: string;
  status: RecoveryItemStatus;
  bytes_restored: number;
  sha256_verified: boolean;
  threat_status: ThreatRiskLabel;
  threat_rationale?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecoveryJob {
  id: string;
  organization_id: string;
  target_device_id?: string | null;
  requested_by_id?: string | null;
  job_type: RecoveryJobType;
  status: RecoveryJobStatus;
  snapshot_time?: string | null;
  destination_path: string;
  destination_type: DestinationType;
  overwrite_policy: OverwritePolicy;
  total_files: number;
  files_restored: number;
  files_failed: number;
  files_skipped: number;
  bytes_restored: number;
  error_message?: string | null;
  requires_approval: boolean;
  approval_request_id?: string | null;
  risk_assessment?: Record<string, any> | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  items?: RecoveryJobItem[];
}

export interface RestoreItemPreview {
  file_id: string;
  file_version_id: string;
  original_path: string;
  target_path: string;
  size_bytes: number;
  version_number: number;
  created_at: string;
  has_conflict: boolean;
  risk_assessment: {
    risk_label: ThreatRiskLabel;
    rationale: string;
    evidence?: Record<string, any>;
    is_safe_to_restore: boolean;
  };
}

export interface RestorePreviewResponse {
  job_type: RecoveryJobType;
  total_files: number;
  total_bytes: number;
  conflicts_count: number;
  risk_summary: Record<string, number>;
  requires_approval: boolean;
  items: RestoreItemPreview[];
}

export interface RecoveryPointOption {
  snapshot_time: string;
  total_files: number;
  risk_label: ThreatRiskLabel;
  threat_summary: string;
}

export interface RansomwareHeuristicsSummary {
  rapid_encryption_detected: number;
  mass_renames_detected: number;
  mass_deletes_detected: number;
  rapid_extension_changes: number;
  entropy_spikes: number;
  unknown_encrypted_extensions: number;
}

export interface RansomwareStatusResponse {
  files_monitored: number;
  threat_score: number;
  threat_level: 'Safe' | 'Low' | 'Medium' | 'High' | 'Critical';
  protected_folders_count: number;
  last_scan?: string | null;
  detection_engine_status: string;
  quarantined_files_count: number;
  active_monitoring: boolean;
  backup_paused: boolean;
  metrics: RansomwareHeuristicsSummary;
}

export interface RansomwareEvent {
  id: string;
  organization_id?: string | null;
  device_id?: string | null;
  device_name?: string | null;
  event_type: string;
  file_path: string;
  risk_score: number;
  severity: string;
  reason: string;
  status: string;
  created_at: string;
  details?: Record<string, any> | null;
}

export interface QuarantineFile {
  id: string;
  organization_id?: string | null;
  device_id?: string | null;
  file_name: string;
  file_path: string;
  sha256_hash: string;
  file_size_bytes: number;
  quarantine_path: string;
  owner_name: string;
  reason: string;
  status: string;
  quarantined_at: string;
  restored_at?: string | null;
  deleted_at?: string | null;
}

export interface ThreatLog {
  id: string;
  action: string;
  threat_type: string;
  file_path?: string | null;
  severity: string;
  created_at: string;
  details?: Record<string, any> | null;
}

export interface SimulateRansomwareResponse {
  message: string;
  threat_score: number;
  threat_level: string;
  events_generated: number;
  quarantined_files: number;
  backup_protection_triggered: boolean;
}



