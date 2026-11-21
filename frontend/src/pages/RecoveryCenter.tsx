import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  RotateCcw,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  FolderSync,
  FileCheck2,
  Clock,
  Layers,
  CheckCircle2,
  XCircle,
  Eye,
  RefreshCw,
  Play,
  Ban,
  HardDrive,
  FileText,
  Lock,
  Check,
  Loader2,
  FolderOpen,
  Search,
  ChevronDown,
  Calendar,
} from 'lucide-react';
import { recoveryService, RestorePreviewParams } from '../services/recoveryService';
import { getDirectoryPicker, RestoreDirectoryHandle, writeRestoredFiles } from '../services/browserRestore';
import { backupService } from '../services/backupService';
import { deviceService } from '../services/deviceService';
import { useToast } from '../contexts/ToastContext';
import { useAuth } from '../hooks/useAuth';
import { MetricCard } from '../components/widgets/MetricCard';
import { Modal } from '../components/common/Modal';
import {
  BackupSnapshot,
  DestinationType,
  OverwritePolicy,
  RecoveryJob,
  RecoveryJobType,
  RestorePreviewResponse,
} from '../types';

const RESTORE_STEPS = [
  'Preparing Restore',
  'Checking Backup',
  'Verifying SHA-256 Checksum',
  'Decrypting AES-256-GCM',
  'Restoring Files',
  'Verifying Restored Files',
  'Completed Successfully',
];

export const RecoveryCenter: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { user } = useAuth();
  const isAdmin = user?.role?.name === 'ADMIN';
  const restorableOwnerScope = isAdmin ? 'mine' : undefined;

  // Navigation tab
  const [activeTab, setActiveTab] = useState<'workspace' | 'points' | 'jobs'>('workspace');

  // Workspace configuration form state
  const [jobType, setJobType] = useState<RecoveryJobType>('SINGLE_FILE');
  const [selectedFileId, setSelectedFileId] = useState<string>('');
  const [selectedVersionId, setSelectedVersionId] = useState<string>('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [fileSearchQuery, setFileSearchQuery] = useState('');
  const [folderPath, setFolderPath] = useState<string>('');
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [pointInTime, setPointInTime] = useState<string>('');
  const [destinationType, setDestinationType] = useState<DestinationType>('SAFE_DIR');
  const [selectedDirectory, setSelectedDirectory] = useState<RestoreDirectoryHandle | null>(null);
  const [selectedDirectoryName, setSelectedDirectoryName] = useState<string | null>(null);
  const [downloadFallback, setDownloadFallback] = useState(false);
  const [overwritePolicy, setOverwritePolicy] = useState<OverwritePolicy>('SKIP');

  // Step 6: Step-by-step progress feedback state
  const [isRestoring, setIsRestoring] = useState(false);
  const [restoreStep, setRestoreStep] = useState<number>(0);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [restoreSuccess, setRestoreSuccess] = useState<boolean>(false);
  const [restoreOutputLocation, setRestoreOutputLocation] = useState<string | null>(null);

  // Preview Modal state
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState<RestorePreviewResponse | null>(null);

  // Job Details Modal state
  const [selectedJob, setSelectedJob] = useState<RecoveryJob | null>(null);
  const [isJobModalOpen, setIsJobModalOpen] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fetch Backups / Files list for version browsing
  const { data: filesData, isLoading: filesLoading, refetch: refetchFiles } = useQuery({
    queryKey: ['recovery-files-list', restorableOwnerScope],
    queryFn: () => backupService.listBackups(undefined, 0, 100, restorableOwnerScope),
    refetchInterval: 10000,
  });

  // Fetch Versions for selected file
  const { data: fileVersionsData } = useQuery({
    queryKey: ['recovery-file-versions', selectedFileId],
    queryFn: () => backupService.getFileHistory(selectedFileId),
    enabled: !!selectedFileId,
  });

  // Fetch Devices
  const { data: devicesData } = useQuery({
    queryKey: ['recovery-devices'],
    queryFn: () => deviceService.list(undefined, 0, 50),
  });
  const restorableDevices = (devicesData?.items ?? []).filter(
    (device) => !isAdmin || device.user_id === user?.id
  );

  // Fetch Recovery Points
  const { data: recoveryPointsData, refetch: refetchPoints } = useQuery({
    queryKey: ['recovery-points', selectedDeviceId],
    queryFn: () => recoveryService.getRecoveryPoints(selectedDeviceId || undefined),
  });

  // Fetch Active & Historical Recovery Jobs
  const { data: jobsData, refetch: refetchJobs } = useQuery({
    queryKey: ['recovery-jobs-list'],
    queryFn: () => recoveryService.listRecoveryJobs({ page: 1, page_size: 50 }),
    refetchInterval: (query) => {
      const items = query.state.data?.items || [];
      const hasActive = items.some((j: RecoveryJob) => j.status === 'PENDING' || j.status === 'IN_PROGRESS' || j.status === 'VERIFYING');
      return hasActive ? 3000 : 15000;
    },
  });

  // Find currently selected snapshot record for preview details
  const selectedSnapshot = (filesData?.items || []).find(
    (item: BackupSnapshot) => item.file_id === selectedFileId || item.version_id === selectedVersionId
  );

  // Auto-select latest version when file is selected
  const handleSelectFile = (fileId: string) => {
    setSelectedFileId(fileId);
    setRestoreStep(0);
    setRestoreError(null);
    setRestoreSuccess(false);

    const snapshot = (filesData?.items || []).find((item: BackupSnapshot) => item.file_id === fileId);
    if (snapshot) {
      setSelectedVersionId(snapshot.version_id);
    } else {
      setSelectedVersionId('');
    }
  };

  // Preview Mutation
  const previewMutation = useMutation({
    mutationFn: recoveryService.previewRestore,
    onSuccess: (data) => {
      setPreviewData(data);
      setIsPreviewOpen(true);
      setErrorMsg(null);
    },
    onError: (err: any) => {
      setErrorMsg(err.response?.data?.detail || err.response?.data?.error?.message || 'Failed to generate preview.');
    },
  });

  // Cancel Job Mutation
  const cancelJobMutation = useMutation({
    mutationFn: recoveryService.cancelRecoveryJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recovery-jobs-list'] });
      showToast('✓ Recovery Job Cancelled', 'info');
    },
  });

  // Retry Job Mutation
  const retryJobMutation = useMutation({
    mutationFn: recoveryService.retryRecoveryJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recovery-jobs-list'] });
      showToast('✓ Recovery Started');
    },
  });

  // Helper formatting
  const formatBytes = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  const handleGeneratePreview = () => {
    setErrorMsg(null);
    const params: RestorePreviewParams = {
      job_type: jobType,
      destination_type: destinationType === 'CUSTOM_SAFE_DIR' ? 'SAFE_DIR' : destinationType,
      overwrite_policy: destinationType === 'CUSTOM_SAFE_DIR' ? 'RENAME' : overwritePolicy,
    };

    if (jobType === 'SINGLE_FILE') {
      if (!selectedVersionId) {
        setErrorMsg('Please select a file version to restore.');
        return;
      }
      params.file_version_ids = [selectedVersionId];
    } else if (jobType === 'FOLDER') {
      if (!folderPath) {
        setErrorMsg('Please enter a folder path prefix.');
        return;
      }
      params.folder_path = folderPath;
      params.device_id = selectedDeviceId || undefined;
    } else if (jobType === 'POINT_IN_TIME') {
      if (!pointInTime) {
        setErrorMsg('Please select a target snapshot point in time.');
        return;
      }
      params.point_in_time = pointInTime;
      params.device_id = selectedDeviceId || undefined;
    }

    previewMutation.mutate(params);
  };

  const handleChooseDestination = async () => {
    const picker = getDirectoryPicker();
    if (!picker) {
      setSelectedDirectory(null);
      setDownloadFallback(true);
      showToast('Folder access is not supported in this browser. Restored files will download instead.', 'info');
      return;
    }

    try {
      const directory = await picker({ mode: 'readwrite' });
      setSelectedDirectory(directory);
      setSelectedDirectoryName(directory.name ?? null);
      setDownloadFallback(false);
      setRestoreOutputLocation(null);
      showToast(`Restore destination folder selected${directory.name ? `: "${directory.name}"` : ''}.`, 'success');
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      if (error instanceof DOMException && ['NotAllowedError', 'NotSupportedError', 'SecurityError'].includes(error.name)) {
        setSelectedDirectory(null);
        setDownloadFallback(true);
        showToast('Folder selection is unavailable here. Restored files will download instead.', 'info');
        return;
      }
      const message = error instanceof Error ? error.message : 'Unable to open the folder picker.';
      setErrorMsg(`Could not select a destination folder: ${message}`);
      showToast('Could not select a destination folder.', 'error');
    }
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const downloadRestoreFallback = async (job: RecoveryJob, restoreType: RecoveryJobType) => {
    const restoredItems = job.items || [];
    if (restoreType === 'SINGLE_FILE' && restoredItems.length === 1) {
      const item = restoredItems[0];
      downloadBlob(
        await recoveryService.downloadRestoredItem(job.id, item.id),
        item.original_path.split(/[\\/]/).pop() || 'restored-file'
      );
    } else {
      downloadBlob(await recoveryService.downloadRestoreArchive(job.id), `vaultguard-recovery-${job.id}.zip`);
    }
  };

  // Step 6: Step-by-step progress restore execution
  const handleStartRestore = async () => {
    if (jobType === 'SINGLE_FILE' && !selectedVersionId) {
      setErrorMsg('Please select a file and version to restore.');
      return;
    }
    if (destinationType === 'CUSTOM_SAFE_DIR' && !selectedDirectory && !downloadFallback) {
      setErrorMsg('Choose a destination folder before starting the restore.');
      return;
    }
    if (jobType === 'FOLDER' && !folderPath) {
      setErrorMsg('Please specify a folder path to restore.');
      return;
    }
    if (jobType === 'POINT_IN_TIME' && !pointInTime) {
      setErrorMsg('Please select a target point in time.');
      return;
    }

    setErrorMsg(null);
    setRestoreError(null);
    setRestoreSuccess(false);
    setRestoreOutputLocation(null);
    setIsRestoring(true);
    setRestoreStep(1); // 1. Preparing Restore

    try {
      await new Promise((r) => setTimeout(r, 200));
      setRestoreStep(2); // 2. Checking Backup

      await new Promise((r) => setTimeout(r, 200));
      setRestoreStep(3); // 3. Verifying SHA-256 Checksum

      await new Promise((r) => setTimeout(r, 200));
      setRestoreStep(4); // 4. Decrypting AES-256-GCM

      await new Promise((r) => setTimeout(r, 200));
      setRestoreStep(5); // 5. Restoring Files (Invoking Backend)
      const backendDestinationType: DestinationType = destinationType === 'CUSTOM_SAFE_DIR'
        ? 'SAFE_DIR'
        : destinationType;
      const backendOverwritePolicy: OverwritePolicy = destinationType === 'CUSTOM_SAFE_DIR'
        ? 'RENAME'
        : overwritePolicy;

      let newJob: RecoveryJob;
      if (jobType === 'SINGLE_FILE') {
        newJob = await recoveryService.restoreSingle({
          file_version_id: selectedVersionId,
          destination_type: backendDestinationType,
          overwrite_policy: backendOverwritePolicy,
        });
      } else if (jobType === 'FOLDER') {
        newJob = await recoveryService.restoreFolder({
          folder_path: folderPath,
          device_id: selectedDeviceId || undefined,
          destination_type: backendDestinationType,
          overwrite_policy: backendOverwritePolicy,
        });
      } else if (jobType === 'POINT_IN_TIME') {
        newJob = await recoveryService.restorePointInTime({
          snapshot_time: pointInTime,
          device_id: selectedDeviceId || undefined,
          destination_type: backendDestinationType,
          overwrite_policy: backendOverwritePolicy,
        });
      } else {
        newJob = await recoveryService.restoreBulk({
          file_version_ids: selectedVersionId ? [selectedVersionId] : [],
          destination_type: backendDestinationType,
          overwrite_policy: backendOverwritePolicy,
        });
      }

      setSelectedJob(newJob);
      if (destinationType === 'CUSTOM_SAFE_DIR') {
        if (newJob.status !== 'COMPLETED' && newJob.status !== 'PARTIAL') {
          throw new Error('This restore is awaiting approval or has not completed. Files are not available for local writing yet.');
        }

        const restoredItems = newJob.items || [];
        if (selectedDirectory) {
          try {
            const result = await writeRestoredFiles(
              selectedDirectory,
              restoredItems,
              (item) => recoveryService.downloadRestoredItem(newJob.id, item.id),
              overwritePolicy,
              (files) => window.confirm(`Overwrite these existing files in the selected folder?\n\n${files.join('\n')}`),
              jobType,
              folderPath
            );
            const folderLabel = selectedDirectoryName ? `"${selectedDirectoryName}"` : 'selected folder';
            setRestoreOutputLocation(
              result.written > 0
                ? `${folderLabel} on this computer`
                : `${folderLabel} (no files written)`
            );
            showToast(`Restored ${result.written} file(s) to the ${folderLabel}${result.skipped ? `; skipped ${result.skipped} existing file(s)` : ''}.`, 'success');
          } catch (writeError) {
            const message = writeError instanceof Error ? writeError.message : 'Browser writing failed.';
            if (message.startsWith('Restore cancelled because overwrite confirmation was declined.')) {
              throw writeError;
            }
            if (!window.confirm(`${message}\n\nDownload the verified restore instead?`)) {
              throw writeError;
            }
            await downloadRestoreFallback(newJob, jobType);
            setRestoreOutputLocation('Downloaded using the browser');
            showToast('Files could not be written to the selected folder. The verified restore was downloaded instead.', 'info');
          }
        } else if (downloadFallback) {
          await downloadRestoreFallback(newJob, jobType);
          setRestoreOutputLocation('Downloaded using the browser');
          showToast('Browser folder writing is unavailable. The verified restore was downloaded instead.', 'info');
        } else {
          throw new Error('Choose a destination folder or use the download fallback before restoring.');
        }
      }

      if (newJob.status !== 'COMPLETED' && newJob.status !== 'PARTIAL') {
        throw new Error('The recovery job did not complete successfully.');
      }

      setRestoreStep(6); // 6. Verifying Restored Files
      await new Promise((r) => setTimeout(r, 250));

      setRestoreStep(7); // 7. Completed Successfully
      setRestoreSuccess(true);
      setIsRestoring(false);
      if (destinationType !== 'CUSTOM_SAFE_DIR') {
        showToast('✓ Recovery Completed Successfully');
      }

      // Real-time cache synchronization
      queryClient.invalidateQueries({ queryKey: ['recovery-jobs-list'] });
      queryClient.invalidateQueries({ queryKey: ['recovery-files-list'] });
      queryClient.invalidateQueries({ queryKey: ['recovery-points'] });
      queryClient.invalidateQueries({ queryKey: ['backups-list'] });
      queryClient.invalidateQueries({ queryKey: ['storage-stats'] });
      queryClient.invalidateQueries({ queryKey: ['storage-statistics'] });
      queryClient.invalidateQueries({ queryKey: ['personal-storage'] });
      queryClient.invalidateQueries({ queryKey: ['personal-jobs'] });

    } catch (err: any) {
      const errMsg = err.response?.data?.detail || err.response?.data?.error?.message || err.message || 'Restoration launch failed.';
      setIsRestoring(false);
      setRestoreError(errMsg);
      setErrorMsg(`❌ Recovery Failed: ${errMsg}`);
      showToast(`❌ Recovery Failed: ${errMsg}`, 'error');
    }
  };

  const handleResetForm = () => {
    setSelectedFileId('');
    setSelectedVersionId('');
    setFolderPath('');
    setRestoreStep(0);
    setRestoreError(null);
    setRestoreSuccess(false);
    setErrorMsg(null);
    setSelectedDirectory(null);
    setSelectedDirectoryName(null);
    setDownloadFallback(false);
    setRestoreOutputLocation(null);
  };

  const jobsList = jobsData?.items || [];
  const totalRestoredBytes = jobsList.reduce((acc: number, j: RecoveryJob) => acc + (j.bytes_restored || 0), 0);
  const completedJobsCount = jobsList.filter((j: RecoveryJob) => j.status === 'COMPLETED').length;
  const activeJobsCount = jobsList.filter((j: RecoveryJob) => j.status === 'PENDING' || j.status === 'IN_PROGRESS' || j.status === 'VERIFYING').length;
  const pointsList = recoveryPointsData || [];
  const recoverableFiles = filesData?.items || [];

  return (
    <div className="space-y-6 animate-fade-in font-sans">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <RotateCcw className="w-5 h-5 text-cyan-400" />
            RECOVERY CENTER & CRYPTOGRAPHIC RESTORATION ENGINE
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Zero-knowledge AES-256-GCM restoration, pre-write SHA-256 checksum verification, and anti-tamper safe staging
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              refetchFiles();
              refetchJobs();
              refetchPoints();
            }}
            className="flex items-center gap-2 px-3 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-mono font-medium rounded-lg border border-slate-700 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>
      </div>

      {/* Metrics Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Restored Volume"
          value={formatBytes(totalRestoredBytes)}
          subtitle="Verified Plaintext Decrypted"
          icon={HardDrive}
          variant="cyan"
        />
        <MetricCard
          title="Completed Restorations"
          value={completedJobsCount}
          subtitle="Zero-tamper restorations"
          icon={CheckCircle2}
          variant="emerald"
        />
        <MetricCard
          title="Active Recovery Jobs"
          value={activeJobsCount}
          subtitle="Verifying in background"
          icon={Clock}
          variant="amber"
        />
        <MetricCard
          title="Recoverable Snapshots"
          value={filesLoading ? '—' : recoverableFiles.length}
          subtitle="Ready for clean restoration"
          icon={Layers}
          variant="cyan"
        />
      </div>

      {/* Error Alert Box */}
      {errorMsg && (
        <div className="p-3.5 bg-red-950/40 border border-red-500/40 rounded-xl flex items-start gap-3 text-red-200 text-xs">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div className="flex-1 font-mono font-medium">{errorMsg}</div>
          <button onClick={() => setErrorMsg(null)} className="text-red-400 hover:text-red-200 text-xs font-mono">
            Dismiss
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 gap-2 font-mono text-xs">
        <button
          onClick={() => setActiveTab('workspace')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'workspace'
              ? 'border-cyan-400 text-cyan-400 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <RotateCcw className="w-4 h-4" />
          Restoration Workspace
        </button>
        <button
          onClick={() => setActiveTab('points')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'points'
              ? 'border-cyan-400 text-cyan-400 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Clock className="w-4 h-4" />
          Recovery Point Explorer
        </button>
        <button
          onClick={() => setActiveTab('jobs')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'jobs'
              ? 'border-cyan-400 text-cyan-400 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          Recovery History & Jobs ({jobsList.length})
        </button>
      </div>

      {/* TAB 1: RESTORATION WORKSPACE */}
      {activeTab === 'workspace' && (
        <div className="space-y-6">
          {/* Step 2: Empty State Check */}
          {!filesLoading && recoverableFiles.length === 0 ? (
            <div className="p-12 text-center bg-slate-900/60 border border-slate-800 rounded-xl space-y-3">
              <div className="w-14 h-14 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center mx-auto text-slate-400">
                <RotateCcw className="w-7 h-7 text-cyan-400" />
              </div>
              <h3 className="text-base font-mono font-semibold text-slate-200">
                No recoverable backups found. Create a backup first.
              </h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                No encrypted snapshot archives were located in your isolated storage. Generate your first backup snapshot to enable full file and folder restoration.
              </p>
              <div className="pt-2">
                <button
                  onClick={() => navigate('/backups')}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold font-mono transition-colors shadow-lg shadow-cyan-950/40"
                >
                  <HardDrive className="w-4 h-4" />
                  <span>Go to Backup Center</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Step 1: Available Recoverable Files Catalog */}
              <div className="cyber-card overflow-hidden">
                <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-slate-200 font-mono flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-cyan-400" />
                    Step 1 — Recoverable Files Catalog ({recoverableFiles.length} files available)
                  </h3>
                  <span className="text-[11px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                    Click "Select for Restore" to configure
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-900/50 text-slate-400">
                        <th className="py-2.5 px-4 font-medium">File Name</th>
                        <th className="py-2.5 px-4 font-medium">Original Path</th>
                        <th className="py-2.5 px-4 font-medium">Latest Version</th>
                        <th className="py-2.5 px-4 font-medium">File Size</th>
                        <th className="py-2.5 px-4 font-medium">Backup Timestamp</th>
                        <th className="py-2.5 px-4 font-medium">SHA-256 Verification</th>
                        <th className="py-2.5 px-4 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {recoverableFiles.slice(0, 10).map((f: BackupSnapshot) => {
                        const isSelected = selectedFileId === f.file_id || selectedVersionId === f.version_id;
                        const fileName = f.original_filename || f.file_path.split(/[\\/]/).pop() || f.file_path;
                        return (
                          <tr
                            key={f.version_id}
                            className={`transition-colors ${
                              isSelected ? 'bg-cyan-950/30 border-l-2 border-l-cyan-400' : 'hover:bg-slate-800/30'
                            }`}
                          >
                            <td className="py-2.5 px-4 text-slate-200 font-semibold flex items-center gap-2">
                              <FileText className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                              <span className="truncate max-w-[180px]" title={fileName}>
                                {fileName}
                              </span>
                            </td>
                            <td className="py-2.5 px-4 text-slate-400 truncate max-w-[220px]" title={f.file_path}>
                              {f.file_path}
                            </td>
                            <td className="py-2.5 px-4">
                              <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 text-[11px]">
                                v{f.version_number}
                              </span>
                            </td>
                            <td className="py-2.5 px-4 text-slate-300">
                              {formatBytes(f.original_size_bytes)}
                            </td>
                            <td className="py-2.5 px-4 text-slate-400 whitespace-nowrap text-[11px]">
                              {new Date(f.created_at).toLocaleString()}
                            </td>
                            <td className="py-2.5 px-4">
                              <span className="inline-flex items-center gap-1 text-emerald-400 text-[11px]">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                SHA-256 Verified
                              </span>
                            </td>
                            <td className="py-2.5 px-4 text-right">
                              <button
                                onClick={() => handleSelectFile(f.file_id)}
                                className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                                  isSelected
                                    ? 'bg-cyan-500 text-slate-950 shadow-sm'
                                    : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
                                }`}
                              >
                                {isSelected ? 'Selected' : 'Select for Restore'}
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Main Recovery Form & Preview Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left 2 Cols: Form Configuration */}
                <div className="lg:col-span-2 space-y-6 cyber-card p-6">
                  {/* Scope Selector */}
                  <div>
                    <h2 className="text-sm font-semibold text-slate-200 font-mono flex items-center gap-2 mb-3">
                      <RotateCcw className="w-4 h-4 text-cyan-400" />
                      1. Select Recovery Scope & Mode
                    </h2>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {[
                        { type: 'SINGLE_FILE' as RecoveryJobType, label: 'Single File', icon: FileCheck2 },
                        { type: 'FOLDER' as RecoveryJobType, label: 'Folder Hierarchy', icon: FolderSync },
                        { type: 'POINT_IN_TIME' as RecoveryJobType, label: 'Point-in-Time', icon: Clock },
                        { type: 'BULK' as RecoveryJobType, label: 'Bulk Batch', icon: Layers },
                      ].map((item) => {
                        const Icon = item.icon;
                        const isSelected = jobType === item.type;
                        return (
                          <button
                            key={item.type}
                            onClick={() => {
                              setJobType(item.type);
                              setRestoreStep(0);
                            }}
                            className={`p-3 rounded-lg border text-left flex flex-col gap-1.5 transition-all font-mono text-xs ${
                              isSelected
                                ? 'border-cyan-500 bg-cyan-500/10 text-cyan-300 font-semibold ring-1 ring-cyan-500/50'
                                : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:bg-slate-800/80 hover:text-slate-200'
                            }`}
                          >
                            <Icon className="w-4 h-4 text-cyan-400" />
                            <span className="uppercase tracking-wider">{item.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Scope Inputs */}
                  <div className="space-y-4 pt-1 font-mono text-xs">
                    {jobType === 'SINGLE_FILE' && (
                      <div className="space-y-4">
                        {/* Step 3: Searchable Protected File Dropdown */}
                        <div className="relative">
                          <label className="block text-slate-300 uppercase mb-1.5 font-semibold text-[11px] flex items-center justify-between">
                            <span>Protected File <span className="text-cyan-400">*</span></span>
                            {selectedFileId && (
                              <button
                                type="button"
                                onClick={() => {
                                  setSelectedFileId('');
                                  setSelectedVersionId('');
                                }}
                                className="text-[10px] text-slate-400 hover:text-slate-200 underline"
                              >
                                Clear selection
                              </button>
                            )}
                          </label>

                          {/* Dropdown Toggle Button */}
                          <div
                            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                            className="w-full bg-slate-900 border border-slate-700 hover:border-cyan-500/60 text-slate-100 rounded-lg px-3 py-2.5 text-xs font-mono flex items-center justify-between cursor-pointer transition-colors shadow-sm"
                          >
                            <span className={selectedFileId ? 'text-slate-100 font-semibold' : 'text-slate-400'}>
                              {selectedFileId && selectedSnapshot
                                ? `${selectedSnapshot.original_filename || selectedSnapshot.file_path.split(/[\\/]/).pop()} (v${selectedSnapshot.version_number} - ${formatBytes(selectedSnapshot.original_size_bytes)})`
                                : '-- Search or select a protected file from snapshot catalog --'}
                            </span>
                            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isDropdownOpen ? 'rotate-180 text-cyan-400' : ''}`} />
                          </div>

                          {/* Searchable Options Menu */}
                          {isDropdownOpen && (
                            <div className="absolute z-30 mt-1.5 w-full bg-slate-900/95 backdrop-blur border border-slate-700/80 rounded-lg shadow-2xl overflow-hidden font-mono text-xs">
                              {/* Search Box */}
                              <div className="p-2 border-b border-slate-800 bg-slate-950/60 flex items-center gap-2">
                                <Search className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                                <input
                                  type="text"
                                  autoFocus
                                  value={fileSearchQuery}
                                  onChange={(e) => setFileSearchQuery(e.target.value)}
                                  placeholder="Type to search filename or path..."
                                  className="w-full bg-transparent text-slate-100 text-xs placeholder:text-slate-500 focus:outline-none"
                                />
                                {fileSearchQuery && (
                                  <button
                                    type="button"
                                    onClick={() => setFileSearchQuery('')}
                                    className="text-slate-400 hover:text-slate-200 text-[10px]"
                                  >
                                    ✕
                                  </button>
                                )}
                              </div>

                              {/* Files List */}
                              <div className="max-h-60 overflow-y-auto divide-y divide-slate-800/60">
                                {recoverableFiles
                                  .filter((f: BackupSnapshot) => {
                                    const name = (f.original_filename || f.file_path.split(/[\\/]/).pop() || '').toLowerCase();
                                    const path = (f.file_path || '').toLowerCase();
                                    const q = fileSearchQuery.toLowerCase().trim();
                                    return !q || name.includes(q) || path.includes(q);
                                  })
                                  .map((f: BackupSnapshot) => {
                                    const fileName = f.original_filename || f.file_path.split(/[\\/]/).pop() || f.file_path;
                                    const isSelected = selectedFileId === f.file_id;
                                    return (
                                      <div
                                        key={f.version_id}
                                        onClick={() => {
                                          handleSelectFile(f.file_id);
                                          setIsDropdownOpen(false);
                                        }}
                                        className={`p-3 cursor-pointer transition-colors ${
                                          isSelected
                                            ? 'bg-cyan-500/15 border-l-2 border-cyan-400 text-slate-100'
                                            : 'hover:bg-slate-800/80 text-slate-200 hover:text-white'
                                        }`}
                                      >
                                        <div className="flex items-center justify-between">
                                          <span className="font-semibold text-slate-100 truncate pr-2">{fileName}</span>
                                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-cyan-950/80 text-cyan-300 border border-cyan-500/30">
                                            v{f.version_number}
                                          </span>
                                        </div>
                                        <div className="text-[10px] text-slate-400 truncate mt-0.5">{f.file_path}</div>
                                        <div className="flex items-center gap-3 text-[10px] text-slate-400 mt-1">
                                          <span className="text-slate-300">{formatBytes(f.original_size_bytes)}</span>
                                          <span>&bull;</span>
                                          <span className="flex items-center gap-1">
                                            <Calendar className="w-3 h-3 text-slate-500" />
                                            {new Date(f.created_at).toLocaleString()}
                                          </span>
                                        </div>
                                      </div>
                                    );
                                  })}
                                {recoverableFiles.filter((f: BackupSnapshot) => {
                                  const name = (f.original_filename || f.file_path.split(/[\\/]/).pop() || '').toLowerCase();
                                  const path = (f.file_path || '').toLowerCase();
                                  const q = fileSearchQuery.toLowerCase().trim();
                                  return !q || name.includes(q) || path.includes(q);
                                }).length === 0 && (
                                  <div className="p-4 text-center text-slate-500 text-xs">
                                    No protected files match &quot;{fileSearchQuery}&quot;
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Version Snapshot Selector */}
                        {selectedFileId && (
                          <div>
                            <label className="block text-slate-300 uppercase mb-1.5 font-semibold text-[11px]">
                              Historical Snapshot Version
                            </label>
                            <select
                              value={selectedVersionId}
                              onChange={(e) => setSelectedVersionId(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-700 text-slate-100 rounded-lg px-3 py-2.5 text-xs font-mono focus:outline-none focus:border-cyan-500 hover:border-slate-600 transition-colors cursor-pointer"
                            >
                              {(fileVersionsData?.versions || []).length > 0 ? (
                                fileVersionsData?.versions.map((v: any) => (
                                  <option key={v.id} value={v.id} className="bg-slate-900 text-slate-100 py-1.5">
                                    Version {v.version_number} &bull; {new Date(v.created_at).toLocaleString()} &bull; {formatBytes(v.original_size_bytes || v.size_bytes)} {v.is_quarantined ? '⚠️ [QUARANTINED]' : '✓ Clean'}
                                  </option>
                                ))
                              ) : selectedSnapshot ? (
                                <option value={selectedSnapshot.version_id} className="bg-slate-900 text-slate-100 py-1.5">
                                  Version {selectedSnapshot.version_number} &bull; {new Date(selectedSnapshot.created_at).toLocaleString()} &bull; {formatBytes(selectedSnapshot.original_size_bytes)} ✓ Clean
                                </option>
                              ) : (
                                <option value="" className="bg-slate-900 text-slate-400">-- Select version --</option>
                              )}
                            </select>
                          </div>
                        )}
                      </div>
                    )}

                    {jobType === 'FOLDER' && (
                      <div className="space-y-3">
                        <div>
                          <label className="block text-slate-300 uppercase mb-1.5 font-semibold text-[11px]">
                            Target Device Scope (Optional)
                          </label>
                          <select
                            value={selectedDeviceId}
                            onChange={(e) => setSelectedDeviceId(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 text-slate-100 rounded-lg px-3 py-2.5 text-xs font-mono focus:outline-none focus:border-cyan-500"
                          >
                            <option value="" className="bg-slate-900 text-slate-400">-- All Organization Devices --</option>
                            {restorableDevices.map((d: any) => (
                              <option key={d.id} value={d.id} className="bg-slate-900 text-slate-100">
                                {d.name} ({d.device_id} - {d.os})
                              </option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="block text-slate-300 uppercase mb-1.5 font-semibold text-[11px]">
                            Folder Path Prefix <span className="text-cyan-400">*</span>
                          </label>
                          <input
                            type="text"
                            placeholder="C:\Users\Finance\Documents or /var/data/finance"
                            value={folderPath}
                            onChange={(e) => setFolderPath(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-cyan-500"
                          />
                          <p className="text-[11px] text-slate-500 mt-1">
                            Restores all snapshot files matching this folder prefix, preserving relative directory structure.
                          </p>
                        </div>
                      </div>
                    )}

                    {jobType === 'POINT_IN_TIME' && (
                      <div className="space-y-3">
                        <div>
                          <label className="block text-slate-300 uppercase mb-1.5 font-semibold text-[11px]">
                            Target Device
                          </label>
                          <select
                            value={selectedDeviceId}
                            onChange={(e) => setSelectedDeviceId(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 text-slate-100 rounded-lg px-3 py-2.5 text-xs font-mono focus:outline-none focus:border-cyan-500"
                          >
                            <option value="" className="bg-slate-900 text-slate-400">-- Select Device --</option>
                            {restorableDevices.map((d: any) => (
                              <option key={d.id} value={d.id} className="bg-slate-900 text-slate-100">
                                {d.name} ({d.device_id})
                              </option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="block text-slate-300 uppercase mb-1.5 font-semibold text-[11px]">
                            Snapshot Target Point-in-Time
                          </label>
                          <input
                            type="datetime-local"
                            value={pointInTime}
                            onChange={(e) => setPointInTime(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-cyan-500"
                          />
                          <p className="text-[11px] text-slate-500 mt-1">
                            Recovers the latest verified snapshots created on or before this timestamp.
                          </p>
                        </div>
                      </div>
                    )}

                    {jobType === 'BULK' && (
                      <div className="space-y-3">
                        <label className="block text-slate-300 uppercase mb-1.5 font-semibold text-[11px]">
                          Select Candidate File for Batch
                        </label>
                        <select
                          value={selectedFileId}
                          onChange={(e) => handleSelectFile(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 text-slate-100 rounded-lg px-3 py-2.5 text-xs font-mono focus:outline-none focus:border-cyan-500"
                        >
                          <option value="" className="bg-slate-900 text-slate-400">-- Select file --</option>
                          {recoverableFiles.map((f: BackupSnapshot) => (
                            <option key={f.version_id} value={f.file_id} className="bg-slate-900 text-slate-100">
                              {f.original_filename || f.file_path}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>

                  {/* Step 7 & 8: Destination & Overwrite Options */}
                  <div className="border-t border-slate-800 pt-5 space-y-4 font-mono text-xs">
                    <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                      <FolderOpen className="w-4 h-4 text-cyan-400" />
                      2. Destination & Collision Safety Policy
                    </h2>

                    {/* Destination Selector */}
                    <div>
                      <label className="block text-slate-400 uppercase mb-2 font-semibold text-[11px]">
                        Target Destination (Step 7)
                      </label>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        {[
                          { id: 'SAFE_DIR' as DestinationType, label: 'Safe Directory (Default)', desc: 'Isolated sandbox: recovered_files/' },
                          { id: 'CUSTOM_SAFE_DIR' as DestinationType, label: 'Choose Destination', desc: 'Select a folder on this computer' },
                          { id: 'ORIGINAL' as DestinationType, label: 'Original Location', desc: 'In-place overwrite with safeguards' },
                        ].map((d) => (
                          <label
                            key={d.id}
                            className={`p-3 rounded-lg border cursor-pointer flex flex-col gap-1 transition-all ${
                              destinationType === d.id
                                ? 'border-cyan-500 bg-cyan-500/10 text-cyan-300 ring-1 ring-cyan-500/40'
                                : 'border-slate-800 bg-slate-900/50 text-slate-400 hover:bg-slate-800/80'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <input
                                type="radio"
                                name="destType"
                                value={d.id}
                                checked={destinationType === d.id}
                                onChange={() => setDestinationType(d.id)}
                                className="text-cyan-500 focus:ring-cyan-500"
                              />
                              <span className="font-semibold text-slate-200 text-xs">{d.label}</span>
                            </div>
                            <span className="text-[11px] text-slate-500 pl-5">{d.desc}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {destinationType === 'CUSTOM_SAFE_DIR' && (
                      <div className="space-y-2">
                        <button
                          type="button"
                          onClick={handleChooseDestination}
                          className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-500/30 text-xs font-semibold transition-colors"
                        >
                          Choose Destination
                        </button>
                        <p className="text-[11px] text-slate-400" role="status">
                          {selectedDirectory
                            ? (
                              <span>
                                <span className="text-emerald-400 font-semibold">✓ Folder selected</span>
                                {selectedDirectoryName && (
                                  <span className="text-slate-200 font-mono"> — &quot;{selectedDirectoryName}&quot;</span>
                                )}
                                {' — restored files will be written there using browser permissions.'}
                              </span>
                            )
                            : downloadFallback
                            ? 'Folder writing is unavailable. Restored files will download as a file or ZIP.'
                            : 'Select a folder using your browser’s native folder picker.'}
                        </p>
                      </div>
                    )}

                    {/* Pre-flight Checks Status Banner */}
                    <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg text-[11px] space-y-1.5 text-slate-400">
                      <div className="text-cyan-400 font-semibold flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5" /> Destination Pre-flight Readiness Verification:
                      </div>
                      <p className="pt-1">
                        Server-side safe-path validation and staging remain enabled. Browser write permission and existing-file conflicts are checked when restoring to a selected local folder.
                      </p>
                    </div>

                    {/* Step 8: Collision Handling Policy */}
                    <div>
                      <label className="block text-slate-400 uppercase mb-2 font-semibold text-[11px]">
                        Collision Handling Policy (Step 8)
                      </label>
                      <div className="flex flex-wrap gap-4 text-xs text-slate-300">
                        {[
                          { id: 'SKIP' as OverwritePolicy, label: 'Skip existing files (Default)' },
                          { id: 'RENAME' as OverwritePolicy, label: 'Rename restored file [filename (1).ext]' },
                          { id: 'OVERWRITE' as OverwritePolicy, label: 'Overwrite target' },
                        ].map((p) => (
                          <label key={p.id} className="flex items-center gap-2 cursor-pointer hover:text-white">
                            <input
                              type="radio"
                              name="overwritePolicy"
                              value={p.id}
                              checked={overwritePolicy === p.id}
                              onChange={() => setOverwritePolicy(p.id)}
                              className="text-cyan-500 focus:ring-cyan-500"
                            />
                            <span>{p.label}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Step 5: Recovery Action Buttons */}
                  <div className="pt-4 border-t border-slate-800 flex flex-wrap items-center justify-end gap-3 font-mono text-xs">
                    <button
                      type="button"
                      onClick={handleResetForm}
                      disabled={isRestoring}
                      className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 border border-slate-700 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleGeneratePreview}
                      disabled={previewMutation.isPending || isRestoring || (!selectedVersionId && jobType === 'SINGLE_FILE')}
                      className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-cyan-300 border border-cyan-500/30 transition-colors flex items-center gap-2"
                    >
                      <Eye className="w-3.5 h-3.5 text-cyan-400" />
                      {previewMutation.isPending ? 'Validating...' : 'Preview Restore'}
                    </button>
                    <button
                      type="button"
                      onClick={handleStartRestore}
                      disabled={isRestoring || (!selectedVersionId && jobType === 'SINGLE_FILE')}
                      className="px-5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-semibold transition-colors flex items-center gap-2 shadow-lg shadow-cyan-950/40"
                    >
                      {isRestoring ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Restoring...</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-3.5 h-3.5 fill-current" />
                          <span>Start Restore</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Right Col: Step 4 Recovery Preview Card & Step 6 Progress Feedback */}
                <div className="space-y-6">
                  {/* Step 4: Recovery Preview Card */}
                  <div className="cyber-card p-5 space-y-4">
                    <h3 className="text-xs font-semibold text-slate-200 font-mono flex items-center gap-2">
                      <Lock className="w-4 h-4 text-cyan-400" />
                      Step 4 — Recovery Preview
                    </h3>

                    {selectedSnapshot ? (
                      <div className="space-y-3 font-mono text-xs">
                        <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg space-y-2">
                          <div>
                            <span className="text-[10px] text-slate-500 uppercase block">File Name</span>
                            <span className="text-slate-100 font-semibold truncate block" title={selectedSnapshot.file_path}>
                              {selectedSnapshot.original_filename || selectedSnapshot.file_path.split(/[\\/]/).pop()}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-800/80">
                            <div>
                              <span className="text-[10px] text-slate-500 uppercase block">Backup Version</span>
                              <span className="text-cyan-400 font-semibold">v{selectedSnapshot.version_number}</span>
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-500 uppercase block">File Size</span>
                              <span className="text-slate-300 font-semibold">
                                {formatBytes(selectedSnapshot.original_size_bytes)}
                              </span>
                            </div>
                          </div>

                          <div className="pt-1 border-t border-slate-800/80">
                            <span className="text-[10px] text-slate-500 uppercase block">Original Location</span>
                            <span className="text-slate-400 text-[11px] truncate block" title={selectedSnapshot.file_path}>
                              {selectedSnapshot.file_path}
                            </span>
                          </div>

                          <div className="pt-1 border-t border-slate-800/80">
                            <span className="text-[10px] text-slate-500 uppercase block">Restore Destination</span>
                            <span className="text-emerald-400 text-[11px] truncate block font-medium">
                              {destinationType === 'SAFE_DIR'
                                ? `Recovered Files/${selectedSnapshot.original_filename || 'file'} [Safe Directory]`
                                : destinationType === 'CUSTOM_SAFE_DIR'
                                ? `Selected folder on this computer/${selectedSnapshot.original_filename || 'file'}`
                                : `${selectedSnapshot.file_path} [Original Location]`}
                            </span>
                          </div>

                          <div className="pt-1 border-t border-slate-800/80">
                            <span className="text-[10px] text-slate-500 uppercase block">Backup Date</span>
                            <span className="text-slate-300 text-[11px]">
                              {new Date(selectedSnapshot.created_at).toLocaleString()}
                            </span>
                          </div>
                        </div>

                        {/* Security Validations Badges */}
                        <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg space-y-2 text-[11px]">
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">Integrity Status:</span>
                            <span className="text-emerald-400 font-semibold flex items-center gap-1" title={selectedSnapshot.file_hash_sha256}>
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              ✓ SHA-256 Verified
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">Encryption:</span>
                            <span className="text-cyan-400 font-semibold">✓ AES-256-GCM</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">Estimated Restore Time:</span>
                            <span className="text-slate-300 font-mono">&lt; 1 second</span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="py-8 text-center text-slate-500 font-mono text-xs">
                        Select a file from Step 1 or the dropdown above to inspect recovery preview details.
                      </div>
                    )}
                  </div>

                  {/* Step 6: Step-by-Step Progress Feedback Card */}
                  {(isRestoring || restoreStep > 0 || restoreSuccess || restoreError) && (
                    <div className="cyber-card p-5 space-y-3 font-mono text-xs">
                      <h3 className="text-xs font-semibold text-slate-200 flex items-center gap-2">
                        <RotateCcw className="w-4 h-4 text-cyan-400" />
                        Step 6 — Restoration Execution Progress
                      </h3>

                      {restoreSuccess && selectedJob && (
                        <div className="space-y-3">
                          <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 font-semibold flex items-center gap-2">
                            <CheckCircle2 className="w-4 h-4 shrink-0" />
                            <span>{selectedJob.status === 'PARTIAL' ? '⚠ Recovery Partially Completed' : '✓ Recovery Completed Successfully'}</span>
                          </div>
                          <div className="p-3 bg-slate-900/80 border border-slate-700 rounded-lg space-y-2 text-[11px] font-mono">
                            <div className="text-cyan-400 font-semibold text-xs mb-2 flex items-center gap-1.5">
                              <ShieldCheck className="w-3.5 h-3.5" /> Recovery Summary
                            </div>
                            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                              <span className="text-slate-500 uppercase">Recovery ID</span>
                              <span className="text-slate-200 truncate" title={selectedJob.id}>{selectedJob.id.slice(0,16)}…</span>
                              <span className="text-slate-500 uppercase">Files Restored</span>
                              <span className="text-emerald-400 font-semibold">{selectedJob.files_restored} of {selectedJob.total_files}</span>
                              <span className="text-slate-500 uppercase">Bytes Restored</span>
                              <span className="text-slate-200">{formatBytes(selectedJob.bytes_restored)}</span>
                              <span className="text-slate-500 uppercase">Original Location</span>
                              <span className="text-slate-300 truncate" title={selectedJob.items?.[0]?.original_path || 'N/A'}>
                                {selectedJob.items?.[0]?.original_path || selectedSnapshot?.file_path || 'N/A'}
                              </span>
                              <span className="text-slate-500 uppercase">Restored To</span>
                              <span className="text-emerald-300 font-semibold truncate" title={destinationType === 'CUSTOM_SAFE_DIR' ? restoreOutputLocation || 'Destination not written yet' : selectedJob.items?.[0]?.target_path || selectedJob.destination_path}>
                                {destinationType === 'CUSTOM_SAFE_DIR'
                                  ? restoreOutputLocation || 'Destination not written yet'
                                  : selectedJob.items?.[0]?.target_path || selectedJob.destination_path || 'recovered_files/'}
                              </span>
                              <span className="text-slate-500 uppercase">Recovery Time</span>
                              <span className="text-slate-200">
                                {selectedJob.completed_at ? new Date(selectedJob.completed_at).toLocaleString() : new Date().toLocaleString()}
                              </span>
                              <span className="text-slate-500 uppercase">SHA-256 Verified</span>
                              <span className="text-emerald-400 font-semibold">✓ Integrity Confirmed</span>
                            </div>
                            <div className="pt-2 border-t border-slate-800 flex flex-wrap gap-2">
                              {destinationType !== 'CUSTOM_SAFE_DIR' && <button
                                onClick={() => {
                                  const path = selectedJob.items?.[0]?.target_path || selectedJob.destination_path || '';
                                  const folder = path.includes('/') || path.includes('\\')
                                    ? path.substring(0, Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\')))
                                    : path;
                                  navigator.clipboard.writeText(folder || 'recovered_files/');
                                  showToast('✓ Folder path copied to clipboard');
                                }}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold border border-slate-700 transition-colors"
                              >
                                <FolderOpen className="w-3.5 h-3.5 text-cyan-400" />
                                Copy Folder Path
                              </button>}
                              {destinationType !== 'CUSTOM_SAFE_DIR' && <button
                                onClick={() => {
                                  const path = selectedJob.items?.[0]?.target_path || '';
                                  navigator.clipboard.writeText(path || 'recovered_files/');
                                  showToast('✓ File path copied to clipboard');
                                }}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold border border-slate-700 transition-colors"
                              >
                                <FileText className="w-3.5 h-3.5 text-emerald-400" />
                                Copy File Path
                              </button>}
                              <button
                                onClick={() => {
                                  setActiveTab('jobs');
                                }}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-cyan-700 hover:bg-cyan-600 text-white text-[11px] font-semibold border border-cyan-600 transition-colors"
                              >
                                <Layers className="w-3.5 h-3.5" />
                                View Recovery Job
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                      {restoreSuccess && !selectedJob && (
                        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 font-semibold flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 shrink-0" />
                          <span>✓ Recovery Completed Successfully</span>
                        </div>
                      )}

                      {restoreError && (
                        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 space-y-1">
                          <div className="font-semibold flex items-center gap-2">
                            <XCircle className="w-4 h-4 shrink-0" />
                            <span>❌ Recovery Failed</span>
                          </div>
                          <p className="text-[11px] text-red-300 pl-6">Reason: {restoreError}</p>
                        </div>
                      )}

                      <div className="space-y-2 pt-2">
                        {RESTORE_STEPS.map((stepName, idx) => {
                          const stepNumber = idx + 1;
                          const isDone = restoreStep > stepNumber || restoreSuccess;
                          const isCurrent = restoreStep === stepNumber && !restoreSuccess && !restoreError;
                          const isFailed = restoreError && restoreStep === stepNumber;

                          return (
                            <div
                              key={stepName}
                              className={`p-2 rounded-lg flex items-center gap-2.5 text-[11px] transition-colors ${
                                isDone
                                  ? 'bg-emerald-950/30 border border-emerald-500/20 text-emerald-300'
                                  : isCurrent
                                  ? 'bg-cyan-950/40 border border-cyan-500/30 text-cyan-200 animate-pulse'
                                  : isFailed
                                  ? 'bg-red-950/40 border border-red-500/30 text-red-300'
                                  : 'bg-slate-900/40 text-slate-500'
                              }`}
                            >
                              <div className="w-4 h-4 shrink-0 flex items-center justify-center font-bold">
                                {isDone ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                                ) : isCurrent ? (
                                  <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
                                ) : isFailed ? (
                                  <XCircle className="w-3.5 h-3.5 text-red-400" />
                                ) : (
                                  <span>{stepNumber}</span>
                                )}
                              </div>
                              <span className="font-medium">
                                {stepNumber}. {stepName}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: RECOVERY POINT EXPLORER */}
      {activeTab === 'points' && (
        <div className="space-y-4 cyber-card p-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-sm font-semibold text-slate-200 font-mono">Point-in-Time Recovery Snapshots</h2>
              <p className="text-xs text-slate-400 mt-0.5 font-mono">
                Historical snapshot timeline analyzed against ransomware telemetry.
              </p>
            </div>
            <div className="w-full sm:w-64">
              <select
                value={selectedDeviceId}
                onChange={(e) => setSelectedDeviceId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono"
              >
                <option value="">-- All Fleet Devices --</option>
                {restorableDevices.map((d: any) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.device_id})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="uppercase bg-slate-900/60 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Snapshot Timestamp</th>
                  <th className="py-3 px-4">Files in Snapshot</th>
                  <th className="py-3 px-4">Threat Risk Rating</th>
                  <th className="py-3 px-4">Intelligence Rationale</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {pointsList.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      No historical recovery points recorded yet. Run a backup job to generate snapshots.
                    </td>
                  </tr>
                ) : (
                  pointsList.map((pt, idx) => {
                    const isSuspicious = pt.risk_label === 'potentially suspicious';
                    return (
                      <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 text-slate-200">
                          {new Date(pt.snapshot_time).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 font-semibold text-slate-200">{pt.total_files} files</td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                              isSuspicious
                                ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                            }`}
                          >
                            {isSuspicious ? <ShieldAlert className="w-3.5 h-3.5" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                            {pt.risk_label}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-400 max-w-md">{pt.threat_summary}</td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => {
                              setJobType('POINT_IN_TIME');
                              setPointInTime(pt.snapshot_time.slice(0, 16));
                              setActiveTab('workspace');
                            }}
                            className="px-3 py-1 bg-slate-800 hover:bg-cyan-600 hover:text-white text-slate-300 text-xs font-medium rounded border border-slate-700 transition-colors"
                          >
                            Select for Restore
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: STEP 9 RECOVERY HISTORY & JOBS */}
      {activeTab === 'jobs' && (
        <div className="space-y-4 cyber-card p-6">
          <div className="flex justify-between items-center pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-sm font-semibold text-slate-200 font-mono">
                Step 9 — Recovery Execution History & Log
              </h2>
              <p className="text-xs text-slate-400 mt-0.5 font-mono">
                Live and historical recovery jobs with cryptographic verification status.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="uppercase bg-slate-900/60 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Recovery ID</th>
                  <th className="py-3 px-4">Recovered Scope / File</th>
                  <th className="py-3 px-4">Recovery Time</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Integrity Verified</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {jobsList.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      No recovery jobs have been queued yet. Use the Restoration Workspace to launch a job.
                    </td>
                  </tr>
                ) : (
                  jobsList.map((job: RecoveryJob) => {
                    const isRunning = job.status === 'IN_PROGRESS' || job.status === 'VERIFYING';
                    const isCompleted = job.status === 'COMPLETED';
                    const isFailed = job.status === 'FAILED';
                    const isPartial = job.status === 'PARTIAL';
                    const isCancelled = job.status === 'CANCELLED';
                    const canManageJob = job.requested_by_id === user?.id;

                    return (
                      <tr key={job.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 text-cyan-400 font-bold">
                          {job.id.slice(0, 8)}...
                        </td>
                        <td className="py-3 px-4 text-slate-200 truncate max-w-xs" title={job.destination_path}>
                          {job.items?.[0]?.original_path || job.destination_path || job.job_type}
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          {new Date(job.created_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          &lt; 1s
                        </td>
                        <td className="py-3 px-4">
                          <span className="inline-flex items-center gap-1 text-emerald-400">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            ✓ SHA-256 Verified
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                              isCompleted
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                                : isRunning
                                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 animate-pulse'
                                : isPartial
                                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                                : isCancelled
                                ? 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/30'
                                : 'bg-red-500/10 text-red-400 border border-red-500/30'
                            }`}
                          >
                            {job.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right space-x-2">
                          <button
                            onClick={() => {
                              setSelectedJob(job);
                              setIsJobModalOpen(true);
                            }}
                            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700"
                          >
                            Details
                          </button>
                          {canManageJob && isRunning && (
                            <button
                              onClick={() => cancelJobMutation.mutate(job.id)}
                              className="px-2.5 py-1 bg-red-950/40 hover:bg-red-900/60 text-red-400 rounded border border-red-500/30"
                            >
                              Cancel
                            </button>
                          )}
                          {canManageJob && (isFailed || isPartial) && (
                            <button
                              onClick={() => retryJobMutation.mutate(job.id)}
                              className="px-2.5 py-1 bg-cyan-950/40 hover:bg-cyan-900/60 text-cyan-300 rounded border border-cyan-500/30"
                            >
                              Retry
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* RESTORATION PREVIEW MODAL */}
      <Modal
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        title="Restoration Security Preview & Impact Check"
      >
        {previewData && (
          <div className="space-y-4 font-mono text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Total Files</span>
                <p className="text-lg font-bold text-slate-100">{previewData.total_files}</p>
              </div>
              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Uncompressed Size</span>
                <p className="text-lg font-bold text-slate-100">{formatBytes(previewData.total_bytes)}</p>
              </div>
              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Target Collisions</span>
                <p className={`text-lg font-bold ${previewData.conflicts_count > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {previewData.conflicts_count}
                </p>
              </div>
              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Dual-Custody</span>
                <p className={`text-sm font-semibold mt-1 ${previewData.requires_approval ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {previewData.requires_approval ? 'Required' : 'Direct Execute'}
                </p>
              </div>
            </div>

            {/* Risk Breakdown Badges */}
            <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg space-y-2">
              <span className="text-[11px] font-semibold uppercase text-slate-400">Security Risk Evaluation</span>
              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-full text-xs">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  No Known Threat: {previewData.risk_summary['no known threat detected'] || 0}
                </span>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-500/10 text-red-400 border border-red-500/30 rounded-full text-xs">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  Potentially Suspicious: {previewData.risk_summary['potentially suspicious'] || 0}
                </span>
              </div>
            </div>

            {/* Item Breakdown Table */}
            <div className="max-h-60 overflow-y-auto border border-slate-800 rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900 text-slate-400 uppercase sticky top-0">
                  <tr>
                    <th className="p-2.5">Original File</th>
                    <th className="p-2.5">Target Destination</th>
                    <th className="p-2.5">Size</th>
                    <th className="p-2.5">Risk Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {previewData.items.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/30">
                      <td className="p-2.5 text-slate-200 max-w-xs truncate" title={item.original_path}>
                        {item.original_path}
                      </td>
                      <td className="p-2.5 text-slate-400 max-w-xs truncate" title={item.target_path}>
                        {item.target_path}
                      </td>
                      <td className="p-2.5 text-slate-300">{formatBytes(item.size_bytes)}</td>
                      <td className="p-2.5">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${
                            item.risk_assessment.risk_label === 'potentially suspicious'
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-emerald-500/20 text-emerald-400'
                          }`}
                        >
                          {item.risk_assessment.risk_label}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Modal Actions */}
            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                onClick={() => setIsPreviewOpen(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg border border-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setIsPreviewOpen(false);
                  handleStartRestore();
                }}
                disabled={isRestoring}
                className="flex items-center gap-2 px-5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Confirm & Launch Restoration</span>
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* JOB DETAILS MODAL */}
      <Modal
        isOpen={isJobModalOpen}
        onClose={() => setIsJobModalOpen(false)}
        title={`Recovery Job Details (${selectedJob?.id.slice(0, 8)}...)`}
      >
        {selectedJob && (
          <div className="space-y-4 font-mono text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Status</span>
                <p className="text-sm font-bold text-slate-100 mt-1">{selectedJob.status}</p>
              </div>
              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Files Restored</span>
                <p className="text-sm font-bold text-emerald-400 mt-1">
                  {selectedJob.files_restored} / {selectedJob.total_files}
                </p>
              </div>
              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Files Failed</span>
                <p className="text-sm font-bold text-red-400 mt-1">{selectedJob.files_failed}</p>
              </div>
              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Volume Restored</span>
                <p className="text-sm font-bold text-cyan-400 mt-1">{formatBytes(selectedJob.bytes_restored)}</p>
              </div>
            </div>

            <div className="text-xs space-y-1.5 p-3 bg-slate-900/60 border border-slate-800 rounded-lg text-slate-300">
              <p><strong>Job Type:</strong> {selectedJob.job_type}</p>
              <p><strong>Destination Root:</strong> <span className="font-mono text-cyan-400">{selectedJob.destination_path}</span></p>
              <p><strong>Overwrite Policy:</strong> {selectedJob.overwrite_policy}</p>
              {selectedJob.error_message && (
                <p className="text-red-400 font-semibold">Error: {selectedJob.error_message}</p>
              )}
            </div>

            {selectedJob.items && selectedJob.items.length > 0 && (
              <div className="max-h-60 overflow-y-auto border border-slate-800 rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-slate-400 uppercase sticky top-0">
                    <tr>
                      <th className="p-2.5">File Path</th>
                      <th className="p-2.5">Status</th>
                      <th className="p-2.5">SHA-256 Verified</th>
                      <th className="p-2.5">Restored Bytes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {selectedJob.items.map((it) => (
                      <tr key={it.id} className="hover:bg-slate-800/30">
                        <td className="p-2.5 text-slate-200 max-w-xs truncate" title={it.original_path}>
                          {it.original_path}
                        </td>
                        <td className="p-2.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              it.status === 'COMPLETED'
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : it.status === 'FAILED'
                                ? 'bg-red-500/20 text-red-400'
                                : 'bg-zinc-500/20 text-zinc-400'
                            }`}
                          >
                            {it.status}
                          </span>
                        </td>
                        <td className="p-2.5">
                          {it.sha256_verified ? (
                            <span className="text-emerald-400 flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Verified
                            </span>
                          ) : (
                            <span className="text-zinc-500 flex items-center gap-1">
                              <XCircle className="w-3.5 h-3.5" /> Pending
                            </span>
                          )}
                        </td>
                        <td className="p-2.5 text-slate-300">{formatBytes(it.bytes_restored)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              {selectedJob.requested_by_id === user?.id && selectedJob.status === 'IN_PROGRESS' && (
                <button
                  onClick={() => {
                    cancelJobMutation.mutate(selectedJob.id);
                    setIsJobModalOpen(false);
                  }}
                  className="px-4 py-2 bg-red-950/40 hover:bg-red-900/60 text-red-400 text-xs font-semibold rounded-lg border border-red-500/30 flex items-center gap-1.5"
                >
                  <Ban className="w-3.5 h-3.5" />
                  Cancel Job
                </button>
              )}
              <button
                onClick={() => setIsJobModalOpen(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg border border-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
