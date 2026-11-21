import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Laptop,
  Building2,
  FolderLock,
  HardDrive,
  History,
  RotateCcw,
  RefreshCw,
  Play,
  ArrowRight,
  ShieldAlert,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { deviceService } from '../services/deviceService';
import { backupService } from '../services/backupService';
import { storageService } from '../services/storageService';
import { threatService } from '../services/threatService';
import { organizationService } from '../services/organizationService';
import { StatusBadge } from '../components/common/StatusBadge';

export const EmployeeDashboard: React.FC = () => {
  const { user } = useAuth();

  // Queries
  const { data: devicesData, refetch: refetchDevices } = useQuery({
    queryKey: ['employee-devices'],
    queryFn: () => deviceService.list(undefined, 0, 10),
  });

  const { data: storageData, refetch: refetchStorage } = useQuery({
    queryKey: ['employee-storage'],
    queryFn: () => storageService.getStorageStatistics(),
  });

  const { data: jobsData, refetch: refetchJobs } = useQuery({
    queryKey: ['employee-jobs'],
    queryFn: () => backupService.listJobs(undefined, undefined, 0, 5),
  });

  const { data: foldersData, refetch: refetchFolders } = useQuery({
    queryKey: ['employee-folders'],
    queryFn: () => backupService.listProtectedFolders(),
  });

  const { data: alertsData, refetch: refetchAlerts } = useQuery({
    queryKey: ['employee-alerts'],
    queryFn: () => threatService.getThreats({ limit: 5 }),
  });

  const { data: orgData } = useQuery({
    queryKey: ['employee-my-organization'],
    queryFn: () => organizationService.list(0, 1),
  });

  const handleRefresh = () => {
    refetchDevices();
    refetchStorage();
    refetchJobs();
    refetchFolders();
    refetchAlerts();
  };

  const devices = devicesData?.items || [];
  const primaryDevice = devices[0];
  const folders = foldersData || [];
  const recentJobs = jobsData?.items || [];
  const alerts = alertsData?.items || [];
  const activeAlerts = alerts.filter((a) => !a.is_resolved);
  const myOrg = orgData?.items?.[0];

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
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono">
              EMPLOYEE WORKSTATION VAULT
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950/80 text-cyan-400 border border-cyan-500/30">
              EMPLOYEE
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Assigned Device Backup & Integrity Protection • {user?.full_name} ({user?.email})
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Organization badge */}
          {myOrg && (
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300">
              <Building2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>{myOrg.name}</span>
            </div>
          )}

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
            <span>Backup Device</span>
          </Link>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Assigned Device */}
        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">My Assigned Device</span>
            <Laptop className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-lg font-bold text-slate-100 font-mono truncate">
            {primaryDevice ? primaryDevice.name : 'No device assigned'}
          </p>
          <div className="flex items-center justify-between text-xs pt-1">
            <span className="text-slate-400 font-mono">{primaryDevice?.os || 'Pending link'}</span>
            {primaryDevice && (
              <StatusBadge status={primaryDevice.status === 'ONLINE' ? 'HEALTHY' : 'WARNING'} />
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
            Folders protected on your device
          </p>
        </div>

        {/* Storage Consumed */}
        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">My Backup Storage</span>
            <HardDrive className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-lg font-bold text-slate-100 font-mono">
            {formatBytes(storageData?.total_stored_bytes || 0)}
          </p>
          <p className="text-xs text-emerald-400 font-mono">
            {storageData?.compression_savings_percent || 0}% compressed space saved
          </p>
        </div>

        {/* Threat Status */}
        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">Device Security</span>
            <ShieldAlert className={`w-4 h-4 ${activeAlerts.length > 0 ? 'text-amber-400' : 'text-emerald-400'}`} />
          </div>
          <p className={`text-lg font-bold font-mono ${activeAlerts.length > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
            {activeAlerts.length === 0 ? 'HEALTHY' : `${activeAlerts.length} ALERTS`}
          </p>
          <p className="text-xs text-slate-400 font-mono">
            Endpoint ransomware monitors active
          </p>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Assigned Device Details */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2">
                <Laptop className="w-4 h-4 text-cyan-400" />
                <span>MY WORKSTATION DETAILS</span>
              </h2>
              <Link to="/devices" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                <span>View Device</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="cyber-card overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 font-mono">
                    <th className="py-2.5 px-3.5 font-medium">Device Name</th>
                    <th className="py-2.5 px-3.5 font-medium">Device Tag</th>
                    <th className="py-2.5 px-3.5 font-medium">OS</th>
                    <th className="py-2.5 px-3.5 font-medium">Status</th>
                    <th className="py-2.5 px-3.5 font-medium text-right">Quick Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {devices.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-500">
                        No device registered under your employee account.{' '}
                        <Link to="/devices" className="text-cyan-400 hover:underline">Register device</Link>.
                      </td>
                    </tr>
                  ) : (
                    devices.map((dev) => (
                      <tr key={dev.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-3.5 font-semibold text-slate-200">
                          {dev.name}
                        </td>
                        <td className="py-3 px-3.5 text-slate-500">{dev.device_id}</td>
                        <td className="py-3 px-3.5 text-slate-400">{dev.os}</td>
                        <td className="py-3 px-3.5">
                          <StatusBadge status={dev.status === 'ONLINE' ? 'HEALTHY' : 'WARNING'} />
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

          {/* Monitored Folders */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2">
                <FolderLock className="w-4 h-4 text-cyan-400" />
                <span>MONITORED BACKUP DIRECTORIES</span>
              </h2>
              <Link to="/protected-folders" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                <span>Manage Folders</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="cyber-card p-4 space-y-3">
              {folders.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-4">
                  No monitored directories set up yet.{' '}
                  <Link to="/protected-folders" className="text-cyan-400 hover:underline">Configure protected directory</Link>.
                </p>
              ) : (
                folders.slice(0, 4).map((f) => (
                  <div key={f.id} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                    <div className="flex items-center gap-2">
                      <FolderLock className="w-4 h-4 text-cyan-400 shrink-0" />
                      <span className="font-mono text-slate-200">{f.folder_path}</span>
                    </div>
                    <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/20">
                      ACTIVE
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent Backup Activity */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2">
                <History className="w-4 h-4 text-cyan-400" />
                <span>MY RECENT BACKUP ACTIVITY</span>
              </h2>
              <Link to="/version-history" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                <span>Version History</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="cyber-card overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 font-mono">
                    <th className="py-2.5 px-3.5 font-medium">Type</th>
                    <th className="py-2.5 px-3.5 font-medium">Status</th>
                    <th className="py-2.5 px-3.5 font-medium">Files</th>
                    <th className="py-2.5 px-3.5 font-medium">Encrypted Stored</th>
                    <th className="py-2.5 px-3.5 font-medium">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {recentJobs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-500">
                        No backup jobs on record for this device.
                      </td>
                    </tr>
                  ) : (
                    recentJobs.map((job) => (
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
        </div>

        {/* Right Column (1 Col) */}
        <div className="space-y-6">
          {/* Recovery Launcher */}
          <div className="cyber-card p-5 border-cyan-500/30 bg-cyan-950/10 space-y-3">
            <div className="flex items-center gap-2">
              <RotateCcw className="w-5 h-5 text-cyan-400" />
              <h3 className="text-sm font-semibold text-slate-100 font-mono">ENDPOINT RESTORATION</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Restore previous clean versions of corrupted, accidentally deleted, or ransomware-affected files on your assigned workstation.
            </p>
            <div className="pt-2">
              <Link
                to="/recovery"
                className="w-full inline-flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold font-mono transition-colors shadow-sm"
              >
                <span>Launch Recovery</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>

          {/* Organization Membership Card */}
          {myOrg && (
            <div className="cyber-card p-4 space-y-3">
              <h3 className="text-xs font-semibold text-slate-300 font-mono uppercase tracking-wider flex items-center gap-1.5">
                <Building2 className="w-4 h-4 text-cyan-400" />
                <span>My Organization</span>
              </h3>
              <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800 space-y-2 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Tenant:</span>
                  <span className="text-slate-100 font-bold">{myOrg.name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Security Contact:</span>
                  <span className="text-slate-300">{myOrg.contact_email}</span>
                </div>
                <div className="flex items-center justify-between border-t border-slate-800 pt-2">
                  <span className="text-slate-400">Status:</span>
                  <span className="text-emerald-400 font-bold">ACTIVE ENROLLMENT</span>
                </div>
              </div>
            </div>
          )}

          {/* Endpoint Threat Alerts */}
          <div className="cyber-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-slate-300 font-mono uppercase tracking-wider">
                Workstation Alerts
              </h3>
              <Link to="/alerts" className="text-[11px] text-cyan-400 hover:underline font-mono">
                View All
              </Link>
            </div>
            {alerts.length === 0 ? (
              <div className="flex items-center gap-2 py-4 text-xs text-emerald-400 justify-center">
                <CheckCircle2 className="w-4 h-4" />
                <span>Endpoint clean • Zero threats active.</span>
              </div>
            ) : (
              <div className="space-y-2">
                {alerts.slice(0, 3).map((alert) => (
                  <div key={alert.id} className="p-2.5 rounded bg-slate-900/80 border border-slate-800 text-xs space-y-1">
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
