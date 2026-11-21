import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Laptop,
  FolderLock,
  HardDrive,
  RotateCcw,
  History,
  CheckCircle2,
  RefreshCw,
  Play,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  Activity,
  Plus,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../contexts/ToastContext';
import { deviceService } from '../services/deviceService';
import { backupService } from '../services/backupService';
import { storageService } from '../services/storageService';
import { threatService } from '../services/threatService';
import { StatusBadge } from '../components/common/StatusBadge';

export const PersonalDashboard: React.FC = () => {
  const { user } = useAuth();
  const { showToast } = useToast();

  // Queries
  const { data: devicesData, refetch: refetchDevices } = useQuery({
    queryKey: ['personal-devices'],
    queryFn: () => deviceService.list(undefined, 0, 10),
  });

  const { data: storageData, refetch: refetchStorage } = useQuery({
    queryKey: ['personal-storage'],
    queryFn: () => storageService.getStorageStatistics(),
  });

  const { data: jobsData, refetch: refetchJobs } = useQuery({
    queryKey: ['personal-jobs'],
    queryFn: () => backupService.listJobs(undefined, undefined, 0, 5),
  });

  const { data: foldersData, refetch: refetchFolders } = useQuery({
    queryKey: ['personal-folders'],
    queryFn: () => backupService.listProtectedFolders(),
  });

  const { data: alertsData, refetch: refetchAlerts } = useQuery({
    queryKey: ['personal-alerts'],
    queryFn: () => threatService.getThreats({ limit: 5 }),
  });

  const handleRefresh = () => {
    refetchDevices();
    refetchStorage();
    refetchJobs();
    refetchFolders();
    refetchAlerts();
    showToast('✓ Device & Backup Status Synced');
  };

  const devices = devicesData?.items || [];
  const primaryDevice = devices[0];
  const folders = foldersData || [];
  const recentJobs = jobsData?.items || [];
  const alerts = alertsData?.items || [];
  const activeAlerts = alerts.filter((a) => !a.is_resolved);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono">
              MY PERSONAL BACKUP VAULT
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950/80 text-cyan-400 border border-cyan-500/30">
              PERSONAL USE
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Secure Personal Cloud Backup, File Versioning & Ransomware Protection • {user?.full_name} ({user?.email})
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 border border-slate-700/80 text-xs font-mono text-slate-300 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
            <span>Sync</span>
          </button>
          <Link
            to="/backups"
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold font-mono transition-colors shadow-lg shadow-cyan-950/40"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Start Backup</span>
          </Link>
          <Link
            to="/recovery"
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-cyan-500/30 text-xs font-semibold font-mono transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Recovery</span>
          </Link>
          <Link
            to="/dashboard/ransomware"
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-red-950/60 hover:bg-red-900/80 text-red-300 border border-red-500/40 text-xs font-semibold font-mono transition-colors"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Ransomware Shield</span>
          </Link>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Device Status */}
        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">Device Status</span>
            <Laptop className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-lg font-bold text-slate-100 font-mono truncate">
            {primaryDevice ? primaryDevice.name : 'No device registered'}
          </p>
          <div className="flex items-center justify-between text-xs pt-1">
            <span className="text-slate-400 font-mono">{primaryDevice?.os || 'Setup needed'}</span>
            {primaryDevice ? (
              <StatusBadge status={primaryDevice.status === 'ONLINE' ? 'HEALTHY' : 'WARNING'} />
            ) : (
              <Link to="/devices" className="text-cyan-400 hover:underline text-[11px] font-semibold">
                Register My Device
              </Link>
            )}
          </div>
        </div>

        {/* Protected Folders */}
        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">Protected Folders</span>
            <FolderLock className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-lg font-bold text-slate-100 font-mono">
            {folders.length}
          </p>
          <p className="text-xs text-slate-400 font-mono">
            Folders monitored for auto-backup
          </p>
        </div>

        {/* Storage Usage */}
        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">Storage Usage</span>
            <HardDrive className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-lg font-bold text-slate-100 font-mono">
            {formatBytes(storageData?.total_stored_bytes || 0)}
          </p>
          <p className="text-xs text-emerald-400 font-mono">
            {storageData?.compression_savings_percent || 0}% compressed space saved
          </p>
        </div>

        {/* Threat Protection */}
        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">Threat Protection</span>
            <ShieldCheck className={`w-4 h-4 ${activeAlerts.length > 0 ? 'text-amber-400' : 'text-emerald-400'}`} />
          </div>
          <p className={`text-lg font-bold font-mono ${activeAlerts.length > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
            {activeAlerts.length === 0 ? 'PROTECTED' : `${activeAlerts.length} THREATS`}
          </p>
          <div className="flex items-center justify-between text-xs pt-1">
            <span className="text-slate-400 font-mono text-[11px]">Anti-ransomware active</span>
            <Link to="/dashboard/ransomware" className="text-cyan-400 hover:underline text-[11px] font-semibold">
              Shield &rarr;
            </Link>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* My Device */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2">
                <Laptop className="w-4 h-4 text-cyan-400" />
                <span>MY DEVICE</span>
              </h2>
              <Link to="/devices" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                <span>Manage Device</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="cyber-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400">
                      <th className="py-2.5 px-3.5 font-medium">Device Name</th>
                      <th className="py-2.5 px-3.5 font-medium">Operating System</th>
                      <th className="py-2.5 px-3.5 font-medium">Device Status</th>
                      <th className="py-2.5 px-3.5 font-medium">Last Connected</th>
                      <th className="py-2.5 px-3.5 font-medium text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {devices.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-6 text-center text-slate-500">
                          No device registered yet.{' '}
                          <Link to="/devices" className="text-cyan-400 hover:underline font-semibold ml-1">
                            Register My Device
                          </Link>
                        </td>
                      </tr>
                    ) : (
                      devices.map((dev) => (
                        <tr key={dev.id} className="hover:bg-slate-800/30 transition-colors">
                          <td className="py-3 px-3.5 font-semibold text-slate-200">
                            {dev.name}
                          </td>
                          <td className="py-3 px-3.5 text-slate-400">{dev.os}</td>
                          <td className="py-3 px-3.5">
                            <StatusBadge status={dev.status === 'ONLINE' ? 'HEALTHY' : 'WARNING'} />
                          </td>
                          <td className="py-3 px-3.5 text-slate-400">
                            {dev.last_seen ? new Date(dev.last_seen).toLocaleTimeString() : 'Never'}
                          </td>
                          <td className="py-3 px-3.5 text-right">
                            <Link
                              to={`/backups?device_id=${dev.id}`}
                              className="px-2.5 py-1 rounded bg-cyan-950/60 hover:bg-cyan-900 text-cyan-400 border border-cyan-500/30 text-[11px]"
                            >
                              Backup Now
                            </Link>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Protected Folders */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2">
                <FolderLock className="w-4 h-4 text-cyan-400" />
                <span>PROTECTED FOLDERS</span>
              </h2>
              <Link to="/protected-folders" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                <span>Configure Folders</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="cyber-card p-4 space-y-3">
              {folders.length === 0 ? (
                <div className="text-center py-5 space-y-2">
                  <p className="text-xs text-slate-500 font-mono">
                    No protected folders configured yet.
                  </p>
                  <Link
                    to="/protected-folders"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 border border-cyan-500/30 text-xs font-mono font-semibold transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Protected Folder</span>
                  </Link>
                </div>
              ) : (
                folders.slice(0, 4).map((f) => (
                  <div key={f.id} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                    <div className="flex items-center gap-2">
                      <FolderLock className="w-4 h-4 text-cyan-400 shrink-0" />
                      <span className="font-mono text-slate-200">{f.folder_path}</span>
                    </div>
                    <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/20">
                      MONITORED
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* My Backups & Recent Activity */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2">
                <History className="w-4 h-4 text-cyan-400" />
                <span>MY BACKUPS & RECENT ACTIVITY</span>
              </h2>
              <Link to="/backup-jobs" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                <span>All Backups</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="cyber-card overflow-hidden">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400">
                    <th className="py-2.5 px-3.5 font-medium">Backup Type</th>
                    <th className="py-2.5 px-3.5 font-medium">Status</th>
                    <th className="py-2.5 px-3.5 font-medium">Files Protected</th>
                    <th className="py-2.5 px-3.5 font-medium">Size</th>
                    <th className="py-2.5 px-3.5 font-medium">Date & Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {recentJobs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-500">
                        No backup jobs recorded yet.{' '}
                        <Link to="/backups" className="text-cyan-400 hover:underline ml-1">Start first backup</Link>
                      </td>
                    </tr>
                  ) : (
                    recentJobs.map((job) => (
                      <tr key={job.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-2.5 px-3.5 text-cyan-400 font-bold">{job.job_type}</td>
                        <td className="py-2.5 px-3.5">
                          <StatusBadge status={job.status === 'COMPLETED' ? 'HEALTHY' : job.status === 'FAILED' ? 'CRITICAL' : 'WARNING'} />
                        </td>
                        <td className="py-2.5 px-3.5 text-slate-300">{job.total_files} files</td>
                        <td className="py-2.5 px-3.5 text-slate-300">{formatBytes(job.bytes_processed)}</td>
                        <td className="py-2.5 px-3.5 text-slate-500">{new Date(job.created_at).toLocaleString()}</td>
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
          {/* Recovery Button & Action Card */}
          <div className="cyber-card p-5 border-cyan-500/30 bg-cyan-950/10 space-y-3">
            <div className="flex items-center gap-2">
              <RotateCcw className="w-5 h-5 text-cyan-400" />
              <h3 className="text-sm font-semibold text-slate-100 font-mono">RECOVERY & RESTORE</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-mono">
              Restore your individual files, folders, or rollback your workstation to a clean point-in-time snapshot before any malware infection.
            </p>
            <div className="pt-2">
              <Link
                to="/recovery"
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold font-mono transition-colors shadow-sm"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Launch Recovery Center</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Link>
            </div>
          </div>

          {/* Storage Usage Breakdown */}
          <div className="cyber-card p-4 space-y-3">
            <h3 className="text-xs font-semibold text-slate-300 font-mono uppercase tracking-wider">
              Storage Usage Details
            </h3>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between text-slate-400">
                <span>Original Files Size:</span>
                <span className="text-slate-200">{formatBytes(storageData?.total_original_bytes || 0)}</span>
              </div>
              <div className="flex items-center justify-between text-slate-400">
                <span>Encrypted Cloud Storage:</span>
                <span className="text-cyan-400 font-bold">{formatBytes(storageData?.total_stored_bytes || 0)}</span>
              </div>
              <div className="flex items-center justify-between text-slate-400">
                <span>Space Saved via Compression:</span>
                <span className="text-emerald-400 font-bold">{formatBytes(storageData?.space_saved_bytes || 0)}</span>
              </div>
              <div className="flex items-center justify-between text-slate-400 border-t border-slate-800 pt-2">
                <span>Compression Efficiency:</span>
                <span className="text-emerald-400 font-bold">{storageData?.compression_savings_percent || 0}%</span>
              </div>
            </div>
          </div>

          {/* Threat Protection Summary */}
          <div className="cyber-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-slate-300 font-mono uppercase tracking-wider flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span>Threat Protection Status</span>
              </h3>
              <Link to="/alerts" className="text-[11px] text-cyan-400 hover:underline font-mono">
                View Alerts
              </Link>
            </div>
            {alerts.length === 0 ? (
              <div className="flex items-center gap-2 py-4 text-xs text-emerald-400 justify-center font-mono">
                <CheckCircle2 className="w-4 h-4" />
                <span>Device is secure. No ransomware detected.</span>
              </div>
            ) : (
              <div className="space-y-2">
                {alerts.slice(0, 3).map((alert) => (
                  <div key={alert.id} className="p-2.5 rounded bg-slate-900/80 border border-slate-800 text-xs space-y-1 font-mono">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200">{alert.threat_name}</span>
                      <span className="text-[10px] font-bold text-amber-400">{alert.severity}</span>
                    </div>
                    <p className="text-[11px] text-slate-400">{new Date(alert.created_at).toLocaleDateString()}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
