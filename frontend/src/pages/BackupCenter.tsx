import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShieldCheck,
  UploadCloud,
  FileCheck2,
  HardDrive,
  Lock,
  Layers,
  RefreshCw,
  AlertCircle,
  FileText,
  Laptop,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Loader2,
  Users,
  Eye,
  RotateCcw,
} from 'lucide-react';
import { backupService } from '../services/backupService';
import { deviceService } from '../services/deviceService';
import { MetricCard } from '../components/widgets/MetricCard';
import { Modal } from '../components/common/Modal';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../contexts/ToastContext';
import { Device, PaginatedData } from '../types';

const DEVICE_ID_STORAGE_KEY = 'vaultguard_device_id';

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
};

const getCurrentDevice = () => {
  const platformHint = navigator.platform || navigator.userAgent;
  const os = /windows/i.test(platformHint)
    ? 'Windows'
    : /mac|iphone|ipad/i.test(platformHint)
      ? 'macOS'
      : /linux|x11/i.test(platformHint)
        ? 'Linux'
        : 'Unknown';
  const existingId = localStorage.getItem(DEVICE_ID_STORAGE_KEY);
  const deviceId = existingId || `VG-${crypto.randomUUID()}`;

  if (!existingId) {
    localStorage.setItem(DEVICE_ID_STORAGE_KEY, deviceId);
  }

  return {
    device_id: deviceId,
    name: `${os} Computer`,
    os,
  };
};

export const BackupCenter: React.FC = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { showToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const isAdmin = user?.role?.name === 'ADMIN';
  const isIndividual = user?.role?.name === 'INDIVIDUAL';
  const ownerScope = isAdmin && searchParams.get('scope') === 'employees' ? 'employees' : isAdmin ? 'mine' : undefined;
  const isEmployeeView = isAdmin && ownerScope === 'employees';
  const canManageFiles = ownerScope !== 'employees';
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [filePath, setFilePath] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  // Maximum upload size enforced client-side before sending (matches nginx + backend: 500 MB)
  const MAX_UPLOAD_BYTES = 500 * 1024 * 1024;
  const [error, setError] = useState<string | null>(null);
  const [enrollError, setEnrollError] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<'idle' | 'scanning' | 'clean' | 'infected' | 'scan_failed'>('idle');
  const [scanDetails, setScanDetails] = useState<string | null>(null);

  const { data: snapshotsData, isLoading: snapshotsLoading, refetch } = useQuery({
    queryKey: ['backups-list', ownerScope],
    queryFn: () => backupService.listBackups(undefined, 0, 50, ownerScope),
    enabled: !isEmployeeView,
    refetchInterval: 10000,
  });

  const {
    data: employeeBackups,
    isLoading: employeeBackupsLoading,
    isError: employeeBackupsFailed,
    error: employeeBackupsError,
    refetch: refetchEmployeeBackups,
  } = useQuery({
    queryKey: ['employee-backups'],
    queryFn: () => backupService.listEmployeeBackups(),
    enabled: isEmployeeView,
  });

  const { data: devicesData } = useQuery({
    queryKey: ['devices-options'],
    queryFn: () => deviceService.list(undefined, 0, 100),
  });

  const availableDevices = (devicesData?.items ?? []).filter(
    (device) => !isAdmin || device.user_id === user?.id
  );

  React.useEffect(() => {
    if (!availableDevices.some((device) => device.id === selectedDevice)) {
      setSelectedDevice(availableDevices[0]?.id ?? '');
    }
  }, [availableDevices, selectedDevice]);

  const manualBackupMutation = useMutation({
    mutationFn: async (payload: Parameters<typeof backupService.manualBackup>[0]) => {
      setScanStatus('scanning');
      setScanDetails(null);
      return backupService.manualBackup(payload);
    },
    onSuccess: () => {
      setScanStatus('clean');
      queryClient.invalidateQueries({ queryKey: ['backups-list'] });
      queryClient.invalidateQueries({ queryKey: ['backups-list-for-history'] });
      queryClient.invalidateQueries({ queryKey: ['recovery-files-list'] });
      queryClient.invalidateQueries({ queryKey: ['recovery-points'] });
      queryClient.invalidateQueries({ queryKey: ['recovery-jobs-list'] });
      queryClient.invalidateQueries({ queryKey: ['backup-jobs'] });
      queryClient.invalidateQueries({ queryKey: ['storage-stats'] });
      queryClient.invalidateQueries({ queryKey: ['storage-statistics'] });
      queryClient.invalidateQueries({ queryKey: ['personal-storage'] });
      queryClient.invalidateQueries({ queryKey: ['personal-jobs'] });
      queryClient.invalidateQueries({ queryKey: ['file-history'] });
      queryClient.invalidateQueries({ queryKey: ['admin-overview'] });
      showToast('✓ Backup Completed — File Scanned Clean & Encrypted');
      setTimeout(() => {
        setIsManualModalOpen(false);
        setFilePath('');
        setSelectedFile(null);
        setError(null);
        setScanStatus('idle');
        setScanDetails(null);
      }, 1200);
    },
    onError: (err: any) => {
      const errorCode = err.response?.data?.error?.code;
      const errMsg = err.response?.data?.error?.message || err.response?.data?.detail || err.message || 'Manual backup failed.';
      const details = err.response?.data?.error?.details;

      if (errorCode === 'MALWARE_DETECTED') {
        setScanStatus('infected');
        const detectionName = details?.detection_name || 'Unknown threat';
        const category = details?.detection_category ? ` [${details.detection_category}]` : '';
        setScanDetails(`${detectionName}${category}`);
        showToast(`🚨 Backup BLOCKED: Malware detected — ${detectionName}`, 'error');
      } else if (
        errorCode === 'SCANNER_UNAVAILABLE' ||
        errorCode === 'SCANNER_TIMEOUT' ||
        errorCode === 'SCANNER_ERROR'
      ) {
        setScanStatus('scan_failed');
        const scannerMessage = errorCode === 'SCANNER_UNAVAILABLE'
          ? 'ClamAV scanner unavailable'
          : errorCode === 'SCANNER_TIMEOUT'
            ? 'ClamAV scan timed out'
            : 'ClamAV scan failed';
        setScanDetails(`${scannerMessage} — backup blocked for security`);
        showToast(`⚠ ${scannerMessage} — backup blocked`, 'error');
      } else if (errorCode === 'FILE_TOO_LARGE') {
        setScanStatus('idle');
        showToast(`❌ File Too Large: ${errMsg}`, 'error');
      } else {
        setScanStatus('idle');
        showToast(`❌ Backup Failed: ${errMsg}`, 'error');
      }
      setError(errMsg);
    },
  });

  const enrollDeviceMutation = useMutation({
    mutationFn: () => deviceService.register(getCurrentDevice()),
    onSuccess: async (device) => {
      queryClient.setQueryData<PaginatedData<Device>>(['devices-options'], (current) => {
        if (!current) return current;
        return {
          ...current,
          items: [device, ...current.items.filter((item) => item.id !== device.id)],
          total: current.items.some((item) => item.id === device.id) ? current.total : current.total + 1,
        };
      });
      await queryClient.invalidateQueries({ queryKey: ['devices-options'] });
      await queryClient.invalidateQueries({ queryKey: ['devices-list'] });
      await queryClient.invalidateQueries({ queryKey: ['devices-count'] });
      await queryClient.invalidateQueries({ queryKey: ['personal-devices'] });
      setSelectedDevice(device.id);
      setEnrollError(null);
      setError(null);
      setIsManualModalOpen(true);
      showToast('✓ Device Registered');
    },
    onError: (err: any) => {
      setEnrollError(err.response?.data?.error?.message || 'Failed to register this device.');
    },
  });

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > MAX_UPLOAD_BYTES) {
        setError(`File too large: ${(file.size / 1024 / 1024).toFixed(1)} MB exceeds the 500 MB limit.`);
        setSelectedFile(null);
        return;
      }
      setFilePath(file.name);
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleSubmitManual = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDevice) {
      setError('Please select an enrolled device.');
      return;
    }
    if (!selectedFile) {
      setError('Please select a file to backup.');
      return;
    }

    manualBackupMutation.mutate({
      device_id: selectedDevice,
      file_path: filePath,
      file: selectedFile,
    });
  };

  const totalSnapshots = snapshotsData?.total ?? 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-cyan-400" />
            {isEmployeeView
              ? 'EMPLOYEE BACKUPS · READ-ONLY'
              : isAdmin
                ? 'MY BACKUPS & ENCRYPTED SNAPSHOTS'
                : 'BACKUP CENTER & ENCRYPTED SNAPSHOTS'}
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {isEmployeeView
              ? 'Organization employee backup usage and status. Select an employee to view their backup and recovery history.'
              : 'Real-time AES-256-GCM encrypted versioned backups stored in isolated MinIO S3 object storage'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => isEmployeeView ? refetchEmployeeBackups() : refetch()}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            title="Refresh Backups"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          {isAdmin && (
            <div className="flex items-center rounded-lg border border-slate-700 p-1">
              <button
                onClick={() => setSearchParams({ scope: 'mine' })}
                className={`px-3 py-1.5 rounded text-xs font-mono ${ownerScope === 'mine' ? 'bg-cyan-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}
              >
                My Backups
              </button>
              <button
                onClick={() => setSearchParams({ scope: 'employees' })}
                className={`px-3 py-1.5 rounded text-xs font-mono ${ownerScope === 'employees' ? 'bg-cyan-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}
              >
                Employee Backups
              </button>
            </div>
          )}
          {canManageFiles && <button
            onClick={() => {
              setEnrollError(null);
              enrollDeviceMutation.mutate();
            }}
            disabled={enrollDeviceMutation.isPending}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-white text-xs font-semibold font-mono transition-colors"
          >
            <Laptop className="w-4 h-4" />
            <span>
              {enrollDeviceMutation.isPending
                ? 'Registering...'
                : isIndividual
                ? 'Register This Device'
                : 'Enroll This Device'}
            </span>
          </button>
          }
          {canManageFiles && <button
            onClick={() => setIsManualModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold font-mono transition-colors shadow-lg shadow-cyan-950/40"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Manual Backup</span>
          </button>
          }
          {canManageFiles && <button
            type="button"
            onClick={() => navigate('/recovery')}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold font-mono transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Restore My Files
          </button>
          }
        </div>
      </div>

      {enrollError && (
        <div role="alert" className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          <span>{enrollError}</span>
        </div>
      )}

      {isEmployeeView ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Organization Employees"
            value={employeeBackupsLoading ? '—' : employeeBackups?.length ?? 0}
            subtitle="In your organization"
            icon={Users}
            variant="cyan"
          />
          <MetricCard
            title="Employee Backup Files"
            value={employeeBackupsLoading ? '—' : employeeBackups?.reduce((sum, item) => sum + item.total_backup_files, 0) ?? 0}
            subtitle="Employee-owned files"
            icon={Layers}
            variant="emerald"
          />
          <MetricCard
            title="Encrypted Storage"
            value={employeeBackupsLoading ? '—' : formatBytes(employeeBackups?.reduce((sum, item) => sum + item.storage_used_bytes, 0) ?? 0)}
            subtitle="Across employee backups"
            icon={HardDrive}
            variant="cyan"
          />
          <MetricCard
            title="Access Mode"
            value="READ ONLY"
            subtitle="No employee file changes"
            icon={Eye}
            variant="emerald"
          />
        </div>
      ) : (
      /* Top Metric Cards */
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Encrypted Snapshots"
          value={snapshotsLoading ? '—' : totalSnapshots}
          subtitle="Immutable version records"
          icon={Layers}
          variant="cyan"
        />
        <MetricCard
          title="Encryption Standard"
          value="AES-256-GCM"
          subtitle="Military-grade authenticated"
          icon={Lock}
          variant="emerald"
        />
        <MetricCard
          title="Compression Engine"
          value="zlib Stream"
          subtitle="Pre-encryption compression"
          icon={FileCheck2}
          variant="cyan"
        />
        <MetricCard
          title="Object Target"
          value="vaultguard-storage"
          subtitle="MinIO S3 isolated bucket"
          icon={HardDrive}
          variant="emerald"
        />
      </div>
      )}

      {isEmployeeView ? (
      <div className="cyber-card overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-200 font-mono flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              Employee Backup Accounts
            </h3>
            <p className="text-xs text-slate-500 mt-1">Employee files and recovery data are visible only to this organization’s Admin.</p>
          </div>
          <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
            {employeeBackups?.length ?? 0} Employees
          </span>
        </div>
        {employeeBackupsLoading ? (
          <div className="py-16 text-center text-slate-500 font-mono text-xs">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-cyan-400" />
            Loading organization employee backups...
          </div>
        ) : employeeBackupsFailed ? (
          <div role="alert" className="py-12 px-4 text-center text-red-300 text-sm">
            {employeeBackupsError instanceof Error ? employeeBackupsError.message : 'Unable to load employee backup data.'}
          </div>
        ) : !employeeBackups?.length ? (
          <div className="py-16 px-4 text-center text-slate-400 text-sm">
            No employees are registered in this organization.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/40 text-slate-400 font-mono">
                  <th className="py-3 px-4 font-medium">Employee</th>
                  <th className="py-3 px-4 font-medium">Email</th>
                  <th className="py-3 px-4 font-medium">Backup Files</th>
                  <th className="py-3 px-4 font-medium">Storage Used</th>
                  <th className="py-3 px-4 font-medium">Last Backup</th>
                  <th className="py-3 px-4 font-medium">Status</th>
                  <th className="py-3 px-4 font-medium">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {employeeBackups.map((employee) => (
                  <tr key={employee.employee_id} className="hover:bg-slate-800/30">
                    <td className="py-3 px-4 text-slate-200 font-semibold">
                      {employee.full_name}
                      {!employee.is_active && <span className="ml-2 text-[10px] text-amber-400">INACTIVE</span>}
                    </td>
                    <td className="py-3 px-4 text-slate-400">{employee.email}</td>
                    <td className="py-3 px-4 text-cyan-300 font-mono">{employee.total_backup_files}</td>
                    <td className="py-3 px-4 text-slate-300 font-mono">{formatBytes(employee.storage_used_bytes)}</td>
                    <td className="py-3 px-4 text-slate-400">
                      {employee.last_backup_at ? new Date(employee.last_backup_at).toLocaleString() : 'Never'}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded border text-[10px] font-mono ${
                        employee.backup_status === 'COMPLETED'
                          ? 'text-emerald-300 bg-emerald-500/10 border-emerald-500/20'
                          : employee.backup_status === 'FAILED'
                            ? 'text-red-300 bg-red-500/10 border-red-500/20'
                            : employee.backup_status === 'NO_BACKUPS'
                              ? 'text-slate-400 bg-slate-500/10 border-slate-500/20'
                              : 'text-amber-300 bg-amber-500/10 border-amber-500/20'
                      }`}>
                        {employee.backup_status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <button
                        type="button"
                        onClick={() => navigate(`/backups/employees/${employee.employee_id}`)}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10 font-mono"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      ) : (
      /* Live Snapshots Table */
      <div className="cyber-card overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200 font-mono flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            Live Backup Snapshot Registry
          </h3>
          <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
            {totalSnapshots} Total Snapshots
          </span>
        </div>

        {snapshotsLoading ? (
          <div className="py-16 text-center text-slate-500 font-mono text-xs">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-cyan-400" />
            Retrieving encrypted snapshot catalog...
          </div>
        ) : (snapshotsData?.items ?? []).length === 0 ? (
          <div className="py-16 px-4 text-center">
            <div className="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto mb-3 text-slate-400">
              <Layers className="w-6 h-6 text-cyan-400" />
            </div>
            <p className="text-sm font-mono text-slate-200 font-semibold mb-1">
              No backup snapshots available.
            </p>
            <p className="text-xs text-slate-400 max-w-md mx-auto mb-4">
              {canManageFiles
                ? 'Your snapshot registry is empty. Create your first encrypted AES-256-GCM backup snapshot to protect your data.'
                : 'No employee backup snapshots are available in this view.'}
            </p>
            {canManageFiles && <button
              onClick={() => setIsManualModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold font-mono transition-colors shadow-lg shadow-cyan-950/40"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Create Backup</span>
            </button>
            }
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/40 text-slate-400 font-mono">
                  <th className="py-3 px-4 font-medium">File Path</th>
                  <th className="py-3 px-4 font-medium">Version</th>
                  <th className="py-3 px-4 font-medium">Original Size</th>
                  <th className="py-3 px-4 font-medium">Encrypted Size</th>
                  <th className="py-3 px-4 font-medium">SHA-256 Integrity</th>
                  <th className="py-3 px-4 font-medium">MinIO Object Path</th>
                  <th className="py-3 px-4 font-medium">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {snapshotsData?.items.map((snap) => (
                  <tr key={snap.version_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 text-slate-200 font-semibold flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      <span className="truncate max-w-[200px]">{snap.file_path}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                        v{snap.version_number}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {(snap.original_size_bytes / 1024).toFixed(1)} KB
                    </td>
                    <td className="py-3 px-4 text-emerald-400 font-bold">
                      {(snap.encrypted_size_bytes / 1024).toFixed(1)} KB
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono text-[11px] truncate max-w-[140px]" title={snap.file_hash_sha256}>
                      {snap.file_hash_sha256.substring(0, 16)}...
                    </td>
                    <td className="py-3 px-4 text-slate-500 truncate max-w-[220px]" title={snap.storage_path}>
                      {snap.storage_path}
                    </td>
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                      {new Date(snap.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      )}

      {/* Manual Backup Modal */}
      {canManageFiles && <Modal isOpen={isManualModalOpen} onClose={() => { setIsManualModalOpen(false); setScanStatus('idle'); setScanDetails(null); setError(null); }} title="Execute Manual Encrypted Backup">
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {/* Scan Status Indicator */}
        {scanStatus === 'scanning' && (
          <div className="mb-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-center gap-2 font-mono">
            <Loader2 className="w-4 h-4 animate-spin shrink-0" />
            <span>🔍 Scanning for malware… Please wait.</span>
          </div>
        )}
        {scanStatus === 'clean' && (
          <div className="mb-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2 font-mono">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>✓ Scan passed — file is CLEAN. Encrypting and uploading…</span>
          </div>
        )}
        {scanStatus === 'infected' && (
          <div className="mb-3 p-3 rounded-lg bg-red-500/10 border border-red-700/30 text-red-400 text-xs font-mono">
            <div className="flex items-center gap-2 font-semibold mb-1">
              <XCircle className="w-4 h-4 shrink-0" />
              <span>🚫 BACKUP BLOCKED — Malware Detected</span>
            </div>
            {scanDetails && <p className="pl-6 text-red-300">Detection: {scanDetails}</p>}
            <p className="pl-6 text-red-500 mt-1">This file has NOT been backed up. A security alert has been created.</p>
          </div>
        )}
        {scanStatus === 'scan_failed' && (
          <div className="mb-3 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-300 text-xs flex items-center gap-2 font-mono">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>⚠ {scanDetails || 'Scan failed — backup blocked for security'}</span>
          </div>
        )}
        <form onSubmit={handleSubmitManual} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">Target Device</label>
            <select
              value={selectedDevice}
              onChange={(e) => setSelectedDevice(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value="">Select Enrolled Device...</option>
              {availableDevices.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.device_id})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">Select File to Backup</label>
            <input
              type="file"
              required
              onChange={handleFileUpload}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-mono file:mr-3 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-cyan-600 file:text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">Recorded File Path</label>
            <input
              type="text"
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
              placeholder="e.g. C:\Confidential\financial_q3.xlsx"
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] font-mono text-slate-400 space-y-1">
            <div className="flex items-center gap-1.5 text-cyan-400 font-semibold">
              <Lock className="w-3.5 h-3.5" /> Pipeline Execution:
            </div>
            <p className="text-amber-400">0. ClamAV malware scan (server-side, mandatory)</p>
            <p>1. Compress with zlib stream</p>
            <p>2. Encrypt with AES-256-GCM (isolated tenant key)</p>
            <p>3. Generate SHA-256 checksum &amp; store in MinIO bucket</p>
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setIsManualModalOpen(false)}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-mono transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={manualBackupMutation.isPending}
              className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-xs font-semibold font-mono text-white transition-colors"
            >
              {manualBackupMutation.isPending
                ? scanStatus === 'scanning'
                  ? 'Scanning for Malware…'
                  : 'Encrypting & Uploading…'
                : 'Upload & Encrypt'}
            </button>
          </div>
        </form>
      </Modal>
      }
    </div>
  );
};

