import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  HardDrive,
  Users,
  ShieldCheck,
  Activity,
  RefreshCw,
  KeyRound,
  Copy,
  Check,
  ArrowRight,
  Cpu,
  ShieldAlert,
  AlertTriangle,
  RotateCcw,
  History,
} from 'lucide-react';
import { organizationService } from '../services/organizationService';
import { deviceService } from '../services/deviceService';
import { storageService } from '../services/storageService';
import { threatService } from '../services/threatService';
import { recoveryService } from '../services/recoveryService';
import { auditService } from '../services/auditService';
import { backupService } from '../services/backupService';
import { useToast } from '../contexts/ToastContext';
import { StatusBadge } from '../components/common/StatusBadge';
import { Modal } from '../components/common/Modal';

export const AdminDashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [copiedCode, setCopiedCode] = useState(false);
  const [isConfirmRegenOpen, setIsConfirmRegenOpen] = useState(false);

  // Queries
  const { data: orgData, refetch: refetchOrg } = useQuery({
    queryKey: ['admin-organization'],
    queryFn: () => organizationService.list(0, 1),
  });

  const { data: inviteData, refetch: refetchInvite } = useQuery({
    queryKey: ['admin-invite-code'],
    queryFn: () => organizationService.getInviteCode(),
  });

  const { data: employeesData, refetch: refetchEmployees } = useQuery({
    queryKey: ['admin-employees'],
    queryFn: () => organizationService.listEmployees(),
  });

  const { data: devicesData, refetch: refetchDevices } = useQuery({
    queryKey: ['admin-devices'],
    queryFn: () => deviceService.list(undefined, 0, 100),
  });

  const { data: storageData, refetch: refetchStorage } = useQuery({
    queryKey: ['admin-storage'],
    queryFn: () => storageService.getStorageStatistics(),
  });

  const { data: backupJobsData, refetch: refetchBackupJobs } = useQuery({
    queryKey: ['admin-recent-backup-jobs'],
    queryFn: () => backupService.listJobs(undefined, undefined, 0, 5),
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
  });

  const { data: recoveryJobsData, refetch: refetchRecovery } = useQuery({
    queryKey: ['admin-recovery-jobs'],
    queryFn: () => recoveryService.listRecoveryJobs({ page: 1, page_size: 5 }),
  });

  const { data: threatsData, refetch: refetchThreats } = useQuery({
    queryKey: ['admin-threats'],
    queryFn: () => threatService.getThreats({ limit: 10 }),
  });

  const { data: auditData, refetch: refetchAudit } = useQuery({
    queryKey: ['admin-audit-logs'],
    queryFn: () => auditService.getRecentLogs(0, 6),
  });

  // Mutation: Regenerate invite code
  const regenMutation = useMutation({
    mutationFn: organizationService.regenerateInviteCode,
    onSuccess: (data) => {
      queryClient.setQueryData(['admin-invite-code'], data);
      setIsConfirmRegenOpen(false);
      showToast('✓ Invite Code Regenerated');
    },
    onError: (err: any) => {
      showToast(err.response?.data?.error?.message || 'Failed to regenerate invite code.', 'error');
    },
  });

  const handleCopyCode = () => {
    const code = inviteData?.invite_code || currentOrg?.invite_code;
    if (code) {
      navigator.clipboard.writeText(code);
      setCopiedCode(true);
      showToast('✓ Invite Code Copied');
      setTimeout(() => setCopiedCode(false), 2500);
    }
  };

  const handleConfirmRegenerate = () => {
    regenMutation.mutate();
  };

  const handleRefreshAll = () => {
    refetchOrg();
    refetchInvite();
    refetchEmployees();
    refetchDevices();
    refetchStorage();
    refetchBackupJobs();
    refetchEmployeeBackups();
    refetchRecovery();
    refetchThreats();
    refetchAudit();
    showToast('✓ Fleet Telemetry Synchronized');
  };

  const currentOrg = orgData?.items?.[0];
  const devices = devicesData?.items || [];
  const employees = employeesData || [];
  const onlineDevices = devices.filter((d) => d.status === 'ONLINE').length;
  const offlineDevices = devices.filter((d) => d.status !== 'ONLINE').length;

  const totalBackupJobs = storageData?.total_backup_jobs || 0;
  const successfulBackupJobs = storageData?.successful_backup_jobs || 0;
  const failedBackupJobs = storageData?.failed_backup_jobs || 0;
  const backupSuccessRate =
    totalBackupJobs > 0 ? Math.round((successfulBackupJobs / totalBackupJobs) * 100) : 100;

  const recoveryItems = recoveryJobsData?.items || [];
  const totalRecoveryJobs = recoveryJobsData?.total || 0;
  const completedRecoveryJobs = recoveryItems.filter((r) => r.status === 'COMPLETED').length;
  const recoverySuccessRate =
    totalRecoveryJobs > 0 ? Math.round((completedRecoveryJobs / totalRecoveryJobs) * 100) : 100;

  const threatItems = threatsData?.items || [];
  const activeThreats = threatItems.filter((t) => !t.is_resolved);

  const storageQuotaBytes = currentOrg?.storage_quota_bytes || 107374182400; // 100GB default
  const storageUsedBytes = storageData?.total_stored_bytes || 0;
  const storageRemainingBytes = Math.max(0, storageQuotaBytes - storageUsedBytes);
  const storageUsagePct = Math.min(100, Math.round((storageUsedBytes / storageQuotaBytes) * 100));

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  // Build map of employee name by user_id
  const employeeMap = new Map<string, string>();
  employees.forEach((e) => {
    employeeMap.set(e.id, e.full_name);
  });

  // Build map of storage used per device
  const deviceStorageMap = new Map<string, number>();
  (storageData?.device_breakdown || []).forEach((b) => {
    deviceStorageMap.set(b.device_id, b.total_bytes);
  });

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono">
              ORGANIZATION CYBER DEFENSE PANE
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-950/80 text-purple-400 border border-purple-500/30">
              ADMIN
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Enterprise Fleet Backup, Disaster Recovery & Ransomware Monitoring • {currentOrg?.name || 'Organization'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefreshAll}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 border border-slate-700/80 text-xs font-mono text-slate-300 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
            <span>Synchronize Fleet</span>
          </button>
        </div>
      </div>

      <section className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link
          to="/backups?scope=mine"
          className="cyber-card p-4 border border-cyan-500/20 hover:border-cyan-400/50 transition-colors"
        >
          <div className="flex items-center gap-2 text-cyan-300 font-mono text-sm font-semibold">
            <HardDrive className="w-4 h-4" />
            My Files
          </div>
          <p className="text-xs text-slate-400 mt-2">Upload, back up, and restore files owned by your Admin account.</p>
        </Link>
        <Link
          to="/backups?scope=employees"
          className="cyber-card p-4 border border-slate-700 hover:border-cyan-400/50 transition-colors"
        >
          <div className="flex items-center gap-2 text-slate-200 font-mono text-sm font-semibold">
            <Users className="w-4 h-4" />
            Employee Backups
          </div>
          <p className="text-xs text-slate-400 mt-2">Review employee backup usage, files, and recovery history in read-only mode.</p>
        </Link>
      </section>

      <section className="cyber-card overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-5 py-4 border-b border-slate-800">
          <div>
            <h2 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2">
              <Users className="w-4 h-4 text-cyan-400" />
              EMPLOYEE BACKUPS
            </h2>
            <p className="text-xs text-slate-400 mt-1">Employee files are displayed separately and are read-only.</p>
          </div>
          <Link
            to="/backups?scope=employees"
            className="text-xs font-mono text-cyan-400 hover:underline"
          >
            View Employee Backup Dashboard →
          </Link>
        </div>
        {employeeBackupsLoading ? (
          <div className="py-10 text-center text-xs font-mono text-slate-400">Loading employee backup summaries...</div>
        ) : employeeBackupsFailed ? (
          <div role="alert" className="py-8 px-5 text-sm text-red-300">
            {employeeBackupsError instanceof Error
              ? employeeBackupsError.message
              : 'Unable to load employee backup summaries.'}
          </div>
        ) : !employeeBackups?.length ? (
          <div className="py-10 px-5 text-center">
            <p className="text-sm text-slate-300">No employees are registered in this organization.</p>
            <p className="text-xs text-slate-500 mt-1">Employees appear here after joining through this organization’s invite.</p>
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
                    <td className="py-3 px-4 text-slate-200 font-semibold">{employee.full_name}</td>
                    <td className="py-3 px-4 text-slate-400">{employee.email}</td>
                    <td className="py-3 px-4 text-cyan-300 font-mono">{employee.total_backup_files}</td>
                    <td className="py-3 px-4 text-slate-300 font-mono">{formatBytes(employee.storage_used_bytes)}</td>
                    <td className="py-3 px-4 text-slate-400">
                      {employee.last_backup_at ? new Date(employee.last_backup_at).toLocaleString() : 'Never'}
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-mono">{employee.backup_status.replace(/_/g, ' ')}</td>
                    <td className="py-3 px-4">
                      <Link
                        to={`/backups/employees/${employee.employee_id}`}
                        className="text-cyan-300 hover:text-cyan-200 hover:underline"
                      >
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Invite Code Quick Banner */}
      <div className="cyber-card p-4 border-cyan-500/30 bg-cyan-950/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0">
            <KeyRound className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-slate-300 uppercase tracking-wider font-semibold">
                Organization Invitation Code:
              </span>
              <span className="font-mono font-bold text-sm text-cyan-300 tracking-wider bg-slate-900 px-2.5 py-1 rounded border border-cyan-500/30">
                {inviteData?.invite_code || currentOrg?.invite_code || 'LOADING...'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Employees join automatically using this code during registration without manual selection.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleCopyCode}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold font-mono transition-colors shadow-sm"
          >
            {copiedCode ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copiedCode ? 'Copied' : 'Copy Code'}</span>
          </button>
          <button
            onClick={() => setIsConfirmRegenOpen(true)}
            disabled={regenMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono border border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${regenMutation.isPending ? 'animate-spin' : ''}`} />
            <span>Regenerate</span>
          </button>
        </div>
      </div>

      {/* Top Fleet Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Enrolled Employees */}
        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">Employee Count</span>
            <Users className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold text-slate-100 font-mono">{employees.length}</p>
          <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
            <span>Enrolled accounts</span>
            <Link to="/organizations" className="text-cyan-400 hover:underline text-[11px]">View roster</Link>
          </div>
        </div>

        {/* Fleet Devices */}
        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">Device Count</span>
            <Cpu className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold text-slate-100 font-mono">{devices.length}</p>
          <div className="flex items-center gap-3 text-xs pt-1 font-mono">
            <span className="text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              {onlineDevices} Online
            </span>
            <span className="text-slate-500 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
              {offlineDevices} Offline
            </span>
          </div>
        </div>

        {/* Storage Quota */}
        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">Storage Usage</span>
            <HardDrive className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold text-slate-100 font-mono">{formatBytes(storageUsedBytes)}</p>
          <div className="flex items-center justify-between text-xs text-slate-400 pt-1 font-mono">
            <span>{formatBytes(storageRemainingBytes)} remaining</span>
            <span className="text-cyan-400 font-bold">{storageUsagePct}%</span>
          </div>
        </div>

        {/* Threat Incidents */}
        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">Ransomware Alerts</span>
            <ShieldAlert className={`w-4 h-4 ${activeThreats.length > 0 ? 'text-red-400' : 'text-emerald-400'}`} />
          </div>
          <p className={`text-2xl font-bold font-mono ${activeThreats.length > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
            {activeThreats.length}
          </p>
          <div className="flex items-center justify-between text-xs pt-1">
            <span className="text-slate-400 font-mono">Active anomalies</span>
            <Link to="/admin/ransomware" className="text-cyan-400 hover:underline text-[11px] font-semibold">
              Ransomware Defense &rarr;
            </Link>
          </div>
        </div>
      </div>

      {/* Secondary Operational Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Backup Success Rate */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase">Backup Success Rate</span>
          <div className="flex items-baseline justify-between">
            <span className="text-lg font-bold text-emerald-400 font-mono">{backupSuccessRate}%</span>
            <span className="text-xs text-slate-400 font-mono">{successfulBackupJobs} / {totalBackupJobs} jobs</span>
          </div>
        </div>

        {/* Failed Backups */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase">Failed Backup Jobs</span>
          <div className="flex items-baseline justify-between">
            <span className={`text-lg font-bold font-mono ${failedBackupJobs > 0 ? 'text-red-400' : 'text-slate-300'}`}>
              {failedBackupJobs}
            </span>
            <span className="text-xs text-slate-400 font-mono">Requires attention</span>
          </div>
        </div>

        {/* Recovery Success Rate */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase">Recovery Success Rate</span>
          <div className="flex items-baseline justify-between">
            <span className="text-lg font-bold text-emerald-400 font-mono">{recoverySuccessRate}%</span>
            <span className="text-xs text-slate-400 font-mono">{totalRecoveryJobs} total restores</span>
          </div>
        </div>

        {/* Compression Efficiency */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase">Compression Savings</span>
          <div className="flex items-baseline justify-between">
            <span className="text-lg font-bold text-cyan-400 font-mono">
              {storageData?.compression_savings_percent || 0}%
            </span>
            <span className="text-xs text-emerald-400 font-mono">
              {formatBytes(storageData?.space_saved_bytes || 0)} saved
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Protected Devices Metadata Table (Zero Personal File Browsing) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-cyan-400" />
                <span>PROTECTED FLEET DEVICES (METADATA ONLY)</span>
              </h2>
              <Link to="/devices" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                <span>View All Devices</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="cyber-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400">
                      <th className="py-2.5 px-3.5 font-medium">Device Name</th>
                      <th className="py-2.5 px-3.5 font-medium">Owner</th>
                      <th className="py-2.5 px-3.5 font-medium">Last Backup</th>
                      <th className="py-2.5 px-3.5 font-medium">Storage Used</th>
                      <th className="py-2.5 px-3.5 font-medium">Backup Status</th>
                      <th className="py-2.5 px-3.5 font-medium">Threat Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {devices.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-6 text-center text-slate-500">
                          No fleet devices enrolled in organization.
                        </td>
                      </tr>
                    ) : (
                      devices.slice(0, 6).map((dev) => {
                        const ownerName = dev.user_id ? employeeMap.get(dev.user_id) || 'Assigned User' : 'Unassigned';
                        const devStorage = deviceStorageMap.get(dev.id) || 0;
                        const isQuarantined = dev.status === 'QUARANTINED';
                        return (
                          <tr key={dev.id} className="hover:bg-slate-800/30 transition-colors">
                            <td className="py-3 px-3.5 font-semibold text-slate-200">{dev.name}</td>
                            <td className="py-3 px-3.5 text-slate-300">{ownerName}</td>
                            <td className="py-3 px-3.5 text-slate-400">
                              {dev.last_seen ? new Date(dev.last_seen).toLocaleTimeString() : 'Never'}
                            </td>
                            <td className="py-3 px-3.5 text-slate-300">{formatBytes(devStorage)}</td>
                            <td className="py-3 px-3.5">
                              <StatusBadge status={dev.status === 'ONLINE' ? 'HEALTHY' : 'WARNING'} />
                            </td>
                            <td className="py-3 px-3.5">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  isQuarantined
                                    ? 'bg-red-950/80 text-red-400 border border-red-500/30'
                                    : 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30'
                                }`}
                              >
                                {isQuarantined ? 'ISOLATED' : 'SECURE'}
                              </span>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Recent Backup Jobs */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2">
                <History className="w-4 h-4 text-cyan-400" />
                <span>RECENT BACKUP JOBS</span>
              </h2>
              <Link to="/backup-jobs" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                <span>View All Jobs</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="cyber-card overflow-hidden">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400">
                    <th className="py-2.5 px-3.5 font-medium">Type</th>
                    <th className="py-2.5 px-3.5 font-medium">Status</th>
                    <th className="py-2.5 px-3.5 font-medium">Files</th>
                    <th className="py-2.5 px-3.5 font-medium">Bytes</th>
                    <th className="py-2.5 px-3.5 font-medium">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {(backupJobsData?.items || []).length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-500">
                        No recent backup jobs recorded.
                      </td>
                    </tr>
                  ) : (
                    (backupJobsData?.items || []).slice(0, 5).map((job) => (
                      <tr key={job.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-2.5 px-3.5 text-cyan-400 font-bold">{job.job_type}</td>
                        <td className="py-2.5 px-3.5">
                          <StatusBadge status={job.status === 'COMPLETED' ? 'HEALTHY' : job.status === 'FAILED' ? 'CRITICAL' : 'WARNING'} />
                        </td>
                        <td className="py-2.5 px-3.5 text-slate-300">{job.total_files}</td>
                        <td className="py-2.5 px-3.5 text-slate-300">{formatBytes(job.bytes_processed)}</td>
                        <td className="py-2.5 px-3.5 text-slate-500">{new Date(job.created_at).toLocaleTimeString()}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Recovery Jobs */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2">
                <RotateCcw className="w-4 h-4 text-cyan-400" />
                <span>RECENT RECOVERY JOBS</span>
              </h2>
              <Link to="/recovery" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                <span>Recovery Center</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="cyber-card overflow-hidden">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400">
                    <th className="py-2.5 px-3.5 font-medium">Type</th>
                    <th className="py-2.5 px-3.5 font-medium">Destination</th>
                    <th className="py-2.5 px-3.5 font-medium">Status</th>
                    <th className="py-2.5 px-3.5 font-medium">Files Restored</th>
                    <th className="py-2.5 px-3.5 font-medium">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {recoveryItems.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-500">
                        No recent restoration jobs recorded.
                      </td>
                    </tr>
                  ) : (
                    recoveryItems.slice(0, 5).map((rJob) => (
                      <tr key={rJob.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-2.5 px-3.5 text-cyan-400 font-bold">{rJob.job_type}</td>
                        <td className="py-2.5 px-3.5 text-slate-300 truncate max-w-[150px]">{rJob.destination_path}</td>
                        <td className="py-2.5 px-3.5">
                          <StatusBadge status={rJob.status === 'COMPLETED' ? 'HEALTHY' : rJob.status === 'FAILED' ? 'CRITICAL' : 'WARNING'} />
                        </td>
                        <td className="py-2.5 px-3.5 text-slate-300">{rJob.files_restored} / {rJob.total_files}</td>
                        <td className="py-2.5 px-3.5 text-slate-500">{new Date(rJob.created_at).toLocaleTimeString()}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column (1 Col) */}
        <div className="space-y-6">
          {/* Privacy Notice Card */}
          <div className="cyber-card p-4 border-slate-800 bg-slate-900/40 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200 font-mono">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              <span>EMPLOYEE PRIVACY PROTOCOL</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed font-mono">
              In strict enforcement of VaultGuard zero-trust RBAC architecture, administrators monitor organization fleet telemetry, storage limits, and security alerts, but cannot directly browse, download, or inspect employee personal file contents.
            </p>
          </div>

          {/* Quick Enrolled Employees list */}
          <div className="cyber-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-slate-300 font-mono uppercase tracking-wider flex items-center gap-1.5">
                <Users className="w-4 h-4 text-cyan-400" />
                <span>Enrolled Employees</span>
              </h3>
              <Link to="/organizations" className="text-[11px] text-cyan-400 hover:underline font-mono">
                Manage
              </Link>
            </div>
            {employees.length === 0 ? (
              <p className="text-xs text-slate-500 py-3 text-center font-mono">No employees enrolled yet.</p>
            ) : (
              <div className="space-y-2">
                {employees.slice(0, 5).map((emp) => (
                  <div key={emp.id} className="flex items-center justify-between p-2 rounded bg-slate-900/80 border border-slate-800 text-xs font-mono">
                    <div>
                      <p className="font-semibold text-slate-200">{emp.full_name}</p>
                      <p className="text-[10px] text-slate-500">{emp.email}</p>
                    </div>
                    <span className="text-[10px] font-bold text-cyan-400 px-1.5 py-0.5 rounded bg-cyan-950/40 border border-cyan-500/20">
                      {emp.role?.name}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Organization Audit Logs */}
          <div className="cyber-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-slate-300 font-mono uppercase tracking-wider flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span>Recent Audit Logs</span>
              </h3>
              <Link to="/settings" className="text-[11px] text-cyan-400 hover:underline font-mono">
                Trail
              </Link>
            </div>
            {(auditData?.items || []).length === 0 ? (
              <p className="text-xs text-slate-500 py-3 text-center font-mono">No audit events recorded.</p>
            ) : (
              <div className="space-y-2">
                {(auditData?.items || []).slice(0, 5).map((log) => (
                  <div key={log.id} className="p-2 rounded bg-slate-900/80 border border-slate-800 text-xs font-mono">
                    <div className="flex items-center justify-between">
                      <span className="text-cyan-400 font-bold">{log.action}</span>
                      <span className="text-[10px] text-slate-500">{new Date(log.created_at).toLocaleTimeString()}</span>
                    </div>
                    <span className="text-[10px] text-slate-400">{log.resource_type || 'System'}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Confirmation Dialog for Invite Code Regeneration */}
      <Modal
        isOpen={isConfirmRegenOpen}
        onClose={() => setIsConfirmRegenOpen(false)}
        title="Regenerate Organization Invite Code"
      >
        <div className="space-y-4 font-mono text-xs">
          <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              Are you sure you want to regenerate the invitation code? Any employee attempting to join with the previous code will be unable to register until you provide them with the new code.
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setIsConfirmRegenOpen(false)}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={regenMutation.isPending}
              onClick={handleConfirmRegenerate}
              className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold transition-colors flex items-center gap-1.5"
            >
              {regenMutation.isPending ? (
                <span className="inline-block w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <RefreshCw className="w-3.5 h-3.5" />
              )}
              <span>Regenerate Now</span>
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
