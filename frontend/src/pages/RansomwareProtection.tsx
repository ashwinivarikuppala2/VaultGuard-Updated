import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  ShieldCheck,
  Play,
  RotateCcw,
  Lock,
  Trash2,
  Download,
  Search,
  RefreshCw,
  FolderLock,
  FileWarning,
  Activity,
  Clock,
  Check,
  Radio,
  FileCheck2,
  Loader2,
} from 'lucide-react';
import { ransomwareService } from '../services/ransomwareService';
import { useToast } from '../contexts/ToastContext';
import { QuarantineFile, RansomwareEvent, ThreatLog } from '../types';

const formatBytes = (bytes: number) => {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export const RansomwareProtection: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState<'timeline' | 'quarantine' | 'logs' | 'recovery'>('timeline');

  // Logs filtering state
  const [logTimeframe, setLogTimeframe] = useState<string>('all');
  const [logSeverity, setLogSeverity] = useState<string>('ALL');
  const [logSearch, setLogSearch] = useState<string>('');

  // 1. Fetch Status & Metrics
  const { data: statusData, refetch: refetchStatus } = useQuery({
    queryKey: ['ransomware-status'],
    queryFn: ransomwareService.getStatus,
    refetchInterval: 5000,
  });

  // 2. Fetch Events Timeline
  const { data: eventsData = [], refetch: refetchEvents } = useQuery({
    queryKey: ['ransomware-events'],
    queryFn: () => ransomwareService.getEvents(50),
    refetchInterval: 5000,
  });

  // 3. Fetch Quarantine Files
  const { data: quarantineFiles = [], refetch: refetchQuarantine } = useQuery({
    queryKey: ['ransomware-quarantine'],
    queryFn: () => ransomwareService.getQuarantineFiles(50),
  });

  // 4. Fetch Threat Logs
  const { data: threatLogs = [], refetch: refetchLogs } = useQuery({
    queryKey: ['ransomware-logs', logTimeframe, logSeverity, logSearch],
    queryFn: () =>
      ransomwareService.getLogs({
        timeframe: logTimeframe,
        severity: logSeverity,
        search: logSearch || undefined,
      }),
  });

  // Mutations
  const simulateMutation = useMutation({
    mutationFn: () => ransomwareService.simulateRansomware(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['ransomware-status'] });
      queryClient.invalidateQueries({ queryKey: ['ransomware-events'] });
      queryClient.invalidateQueries({ queryKey: ['ransomware-quarantine'] });
      queryClient.invalidateQueries({ queryKey: ['ransomware-logs'] });
      queryClient.invalidateQueries({ queryKey: ['personal-alerts'] });
      showToast(
        `🧪 TEST — ${data.message} Simulated score: ${data.threat_score} [${data.threat_level}]`,
        'error'
      );
    },
    onError: (err: any) => {
      showToast(err.response?.data?.message || 'Simulation failed.', 'error');
    },
  });

  const resolveMutation = useMutation({
    mutationFn: () => ransomwareService.resolveAllThreats(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ransomware-status'] });
      queryClient.invalidateQueries({ queryKey: ['ransomware-events'] });
      queryClient.invalidateQueries({ queryKey: ['ransomware-logs'] });
      showToast('✓ Threat status normalized to Safe. Automatic protection reset.', 'success');
    },
    onError: (err: any) => {
      showToast(err.response?.data?.message || 'Failed to normalize threat score.', 'error');
    },
  });

  const restoreQuarantineMutation = useMutation({
    mutationFn: (quarantineId: string) =>
      ransomwareService.restoreQuarantineFile({ quarantine_id: quarantineId, destination: 'ORIGINAL' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ransomware-quarantine'] });
      queryClient.invalidateQueries({ queryKey: ['ransomware-status'] });
      queryClient.invalidateQueries({ queryKey: ['ransomware-logs'] });
      showToast('✓ Quarantined file restored successfully.', 'success');
    },
    onError: (err: any) => {
      showToast(err.response?.data?.message || 'Failed to restore file.', 'error');
    },
  });

  const deleteQuarantineMutation = useMutation({
    mutationFn: (quarantineId: string) => ransomwareService.deleteQuarantineFile(quarantineId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ransomware-quarantine'] });
      queryClient.invalidateQueries({ queryKey: ['ransomware-status'] });
      queryClient.invalidateQueries({ queryKey: ['ransomware-logs'] });
      showToast('✓ Malicious quarantined file permanently purged.', 'info');
    },
    onError: (err: any) => {
      showToast(err.response?.data?.message || 'Failed to delete file.', 'error');
    },
  });

  const handleExportCsv = async () => {
    try {
      await ransomwareService.exportLogsCsv({
        timeframe: logTimeframe,
        severity: logSeverity,
        search: logSearch || undefined,
      });
      showToast('✓ Threat logs CSV exported successfully.', 'success');
    } catch {
      showToast('Failed to export CSV.', 'error');
    }
  };

  const threatScore = statusData?.threat_score || 0;
  const threatLevel = statusData?.threat_level || 'Safe';
  const isHighRisk = threatLevel === 'High' || threatLevel === 'Critical' || threatScore >= 60;

  const getScoreColor = (score: number) => {
    if (score >= 81) return 'text-red-500 border-red-500/50 bg-red-500/10';
    if (score >= 61) return 'text-orange-500 border-orange-500/50 bg-orange-500/10';
    if (score >= 41) return 'text-amber-400 border-amber-400/50 bg-amber-400/10';
    if (score >= 21) return 'text-yellow-300 border-yellow-300/50 bg-yellow-300/10';
    return 'text-emerald-400 border-emerald-400/50 bg-emerald-400/10';
  };

  const getScoreBarColor = (score: number) => {
    if (score >= 81) return 'bg-gradient-to-r from-red-600 to-rose-500';
    if (score >= 61) return 'bg-gradient-to-r from-orange-500 to-amber-500';
    if (score >= 41) return 'bg-gradient-to-r from-yellow-500 to-amber-400';
    return 'bg-gradient-to-r from-emerald-500 to-cyan-500';
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* 1. Critical Threat Banner (Triggers on High / Critical Threat Detection) */}
      {isHighRisk && (
        <div className="p-4 rounded-xl border border-red-500/60 bg-red-950/40 backdrop-blur shadow-2xl shadow-red-950/40 animate-pulse">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <ShieldAlert className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />
              <div>
                <h2 className="text-sm font-bold font-mono uppercase tracking-wide text-red-300 flex items-center gap-2">
                  <span>CRITICAL RANSOMWARE ACTIVITY DETECTED</span>
                  <span className="px-2 py-0.5 rounded text-[10px] bg-red-500 text-white font-semibold">
                    Score: {threatScore}/100 [{threatLevel.toUpperCase()}]
                  </span>
                </h2>
                <p className="text-xs text-red-200/90 font-mono mt-1">
                  Automated Proactive Defense engaged: All scheduled backups paused. Snapshots set to immutable
                  append-only mode to prevent corruption. Malicious files isolated.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => resolveMutation.mutate()}
                disabled={resolveMutation.isPending}
                className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-mono font-semibold transition-colors shadow flex items-center gap-1.5"
              >
                <Check className="w-3.5 h-3.5" />
                Resolve / Normalize
              </button>
              <button
                onClick={() => setActiveTab('quarantine')}
                className="px-3 py-1.5 rounded-lg bg-slate-900 border border-red-500/40 hover:bg-slate-800 text-red-200 text-xs font-mono transition-colors"
              >
                Quarantined Files ({statusData?.quarantined_files_count || 0})
              </button>
              <button
                onClick={() => navigate('/recovery')}
                className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-mono font-semibold transition-colors"
              >
                Launch Recovery Center &rarr;
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Top Header & Primary Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 text-xs font-mono uppercase tracking-widest mb-1">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            <span>Autonomous Heuristic Defense</span>
          </div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-white flex items-center gap-3">
            Ransomware Protection & Threat Intelligence
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Real-time behavioral entropy monitoring, canary decoy tripwires, and automated containment engine.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 font-mono text-xs">
          {/* Active Engine Badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="font-semibold text-emerald-400">ENGINE ACTIVE</span>
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => {
              refetchStatus();
              refetchEvents();
              refetchQuarantine();
              refetchLogs();
              showToast('Refreshed ransomware telemetry.', 'info');
            }}
            className="p-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            title="Refresh Metrics"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {/* Simulation Mode Button */}
          <button
            onClick={() => simulateMutation.mutate()}
            disabled={simulateMutation.isPending}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-amber-600 to-rose-600 hover:from-amber-500 hover:to-rose-500 disabled:opacity-50 text-white font-semibold transition-all shadow-lg shadow-amber-950/30 flex items-center gap-2"
          >
            {simulateMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
            <span>Simulate Ransomware Attack</span>
          </button>
        </div>
      </div>

      {/* 3. Threat Dashboard Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Threat Score Gauge */}
        <div className={`cyber-card p-5 border rounded-xl flex flex-col justify-between ${getScoreColor(threatScore)}`}>
          <div>
            <div className="flex items-center justify-between text-xs font-mono uppercase mb-2">
              <span className="font-semibold">Threat Score</span>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider">
                {threatLevel}
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold font-mono">{threatScore}</span>
              <span className="text-xs text-slate-400 font-mono">/ 100</span>
            </div>
          </div>
          {/* Progress Bar */}
          <div className="mt-4">
            <div className="w-full bg-slate-900/80 rounded-full h-2 overflow-hidden border border-slate-800">
              <div
                className={`h-full transition-all duration-500 ${getScoreBarColor(threatScore)}`}
                style={{ width: `${Math.min(100, Math.max(5, threatScore))}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-1">
              <span>0 (Safe)</span>
              <span>50 (Moderate)</span>
              <span>100 (Critical)</span>
            </div>
          </div>
        </div>

        {/* Metric 2: Files Monitored */}
        <div className="cyber-card p-5 border border-slate-800 rounded-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase mb-2">
              <span>Files Monitored</span>
              <FolderLock className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold font-mono text-slate-100">
                {statusData?.files_monitored || 0}
              </span>
              <span className="text-xs text-slate-400 font-mono">files</span>
            </div>
          </div>
          <div className="mt-3 text-[11px] font-mono text-slate-400 flex items-center justify-between border-t border-slate-800/80 pt-2">
            <span>Protected Folders:</span>
            <span className="text-cyan-400 font-semibold">{statusData?.protected_folders_count || 0} directories</span>
          </div>
        </div>

        {/* Metric 3: Quarantined Suspicious Payloads */}
        <div className="cyber-card p-5 border border-slate-800 rounded-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase mb-2">
              <span>Quarantined Files</span>
              <Lock className="w-4 h-4 text-amber-400" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold font-mono text-amber-300">
                {statusData?.quarantined_files_count || 0}
              </span>
              <span className="text-xs text-slate-400 font-mono">isolated</span>
            </div>
          </div>
          <div className="mt-3 text-[11px] font-mono text-slate-400 flex items-center justify-between border-t border-slate-800/80 pt-2">
            <span>Sandbox Isolation:</span>
            <span className="text-emerald-400 font-semibold">Active &bull; Sandboxed</span>
          </div>
        </div>

        {/* Metric 4: Protection Status */}
        <div className="cyber-card p-5 border border-slate-800 rounded-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase mb-2">
              <span>Automatic Protection</span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-xl font-bold font-mono ${statusData?.backup_paused ? 'text-red-400' : 'text-emerald-400'}`}>
                {statusData?.backup_paused ? 'BACKUP PAUSED' : 'MONITORING'}
              </span>
            </div>
          </div>
          <div className="mt-3 text-[11px] font-mono text-slate-400 flex items-center justify-between border-t border-slate-800/80 pt-2">
            <span>Last Heuristic Scan:</span>
            <span className="text-slate-300 font-mono">
              {statusData?.last_scan ? new Date(statusData.last_scan).toLocaleTimeString() : 'Just now'}
            </span>
          </div>
        </div>
      </div>

      {/* 4. Real-time Monitoring & Metrics on Protected Folders (Heuristics Anomaly Breakdown) */}
      <div className="cyber-card p-5 rounded-xl border border-slate-800 font-mono text-xs">
        <div className="flex items-center justify-between mb-4 border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <h2 className="font-semibold text-slate-200 uppercase tracking-wide">
              Behavioral Heuristic Sensor Matrix
            </h2>
          </div>
          <span className="text-[11px] text-slate-400">Sliding Window: 60-Second Entropy & Burst Profiling</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            {
              label: 'Rapid File Encryption',
              count: statusData?.metrics?.rapid_encryption_detected || 0,
              desc: 'High rate cipher writes',
              badge: 'Entropy > 7.5',
            },
            {
              label: 'Mass File Renames',
              count: statusData?.metrics?.mass_renames_detected || 0,
              desc: 'Burst rename pattern',
              badge: '> 25 / min',
            },
            {
              label: 'Mass File Deletes',
              count: statusData?.metrics?.mass_deletes_detected || 0,
              desc: 'VSS / document wipe',
              badge: '> 30 / min',
            },
            {
              label: 'Rapid Extension Changes',
              count: statusData?.metrics?.rapid_extension_changes || 0,
              desc: 'Known extension mutation',
              badge: '.locked, .wncry',
            },
            {
              label: 'Entropy Spikes',
              count: statusData?.metrics?.entropy_spikes || 0,
              desc: 'Shannon entropy surge',
              badge: '7.8+ bits/byte',
            },
            {
              label: 'Unknown Encrypted Suffix',
              count: statusData?.metrics?.unknown_encrypted_extensions || 0,
              desc: 'Zero-day crypto signature',
              badge: 'Heuristic Alert',
            },
          ].map((item, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-lg border flex flex-col justify-between transition-colors ${
                item.count > 0
                  ? 'bg-red-500/10 border-red-500/40 text-red-200'
                  : 'bg-slate-900/60 border-slate-800 text-slate-400'
              }`}
            >
              <div>
                <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">
                  {item.label}
                </span>
                <span className={`text-xl font-bold font-mono ${item.count > 0 ? 'text-red-400' : 'text-slate-200'}`}>
                  {item.count}
                </span>
              </div>
              <div className="mt-2 pt-1 border-t border-slate-800/60 text-[10px] text-slate-400">
                <span>{item.badge}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 5. Navigation Tabs */}
      <div className="border-b border-slate-800 flex items-center justify-between">
        <div className="flex space-x-1 font-mono text-xs">
          {[
            { id: 'timeline', label: 'Detection Timeline', icon: Clock, count: eventsData.length },
            { id: 'quarantine', label: 'Quarantine Sandbox', icon: Lock, count: quarantineFiles.length },
            { id: 'logs', label: 'Threat Logs & Forensics', icon: FileWarning, count: threatLogs.length },
            { id: 'recovery', label: 'Clean Recovery Integration', icon: RotateCcw },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium transition-all ${
                  isActive
                    ? 'border-cyan-500 text-cyan-300 bg-cyan-500/5'
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                <Icon className="w-4 h-4 text-cyan-400" />
                <span>{tab.label}</span>
                {tab.count !== undefined && (
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${isActive ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-800 text-slate-400'}`}>
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {activeTab === 'logs' && (
          <button
            onClick={handleExportCsv}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-200 text-xs font-mono transition-colors shadow-sm"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span>Export CSV</span>
          </button>
        )}
      </div>

      {/* 6. Tab Content Panels */}
      {/* Tab 1: Detection Timeline */}
      {activeTab === 'timeline' && (
        <div className="cyber-card rounded-xl border border-slate-800 overflow-hidden font-mono text-xs">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
            <h3 className="font-semibold text-slate-200 uppercase tracking-wide">
              Live Threat Timeline ({eventsData.length} Events)
            </h3>
            <span className="text-[11px] text-slate-400">Chronological telemetry anomaly audit</span>
          </div>

          {eventsData.length === 0 ? (
            <div className="py-16 text-center text-slate-500 font-mono">
              <ShieldCheck className="w-10 h-10 text-emerald-400/60 mx-auto mb-3" />
              <p className="text-sm font-semibold text-slate-300">All Systems Nominal &bull; No Active Threats</p>
              <p className="text-xs text-slate-500 mt-1">Continuous behavioral heuristic scanner is monitoring protected files.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] text-slate-400 uppercase tracking-wider">
                    <th className="py-3 px-4">Time</th>
                    <th className="py-3 px-4">Anomaly Event</th>
                    <th className="py-3 px-4">File Path</th>
                    <th className="py-3 px-4">Device</th>
                    <th className="py-3 px-4">Risk Score</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {eventsData.map((ev: RansomwareEvent) => {
                    const isCritical = ev.severity === 'CRITICAL' || ev.risk_score >= 80;
                    return (
                      <tr key={ev.id} className="hover:bg-slate-900/50 transition-colors">
                        <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                          {new Date(ev.created_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 font-semibold text-slate-200">
                          <div className="flex items-center gap-1.5">
                            <span className={`w-2 h-2 rounded-full ${isCritical ? 'bg-red-400' : 'bg-amber-400'}`} />
                            <span>{ev.event_type}</span>
                          </div>
                          <span className="text-[10px] text-slate-400 block mt-0.5 max-w-xs truncate" title={ev.reason}>
                            {ev.reason}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-300 max-w-sm truncate" title={ev.file_path}>
                          {ev.file_path}
                        </td>
                        <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                          {ev.device_name || 'Windows Endpoint'}
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                            ev.risk_score >= 80
                              ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                              : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                          }`}>
                            {ev.risk_score} / 100
                          </span>
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            ev.status === 'SIMULATED'
                              ? 'bg-violet-950 text-violet-300 border border-violet-600/60'
                              : ev.status === 'ACTIVE'
                              ? 'bg-red-950 text-red-400 border border-red-700/50'
                              : 'bg-emerald-950 text-emerald-400 border border-emerald-700/50'
                          }`}>
                            {ev.status === 'SIMULATED' ? 'SIMULATED (TEST)' : ev.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          <button
                            onClick={() => navigate('/recovery')}
                            className="px-2.5 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-[11px] font-semibold transition-colors"
                          >
                            Restore Clean Version
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Quarantine Sandbox */}
      {activeTab === 'quarantine' && (
        <div className="cyber-card rounded-xl border border-slate-800 overflow-hidden font-mono text-xs">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
            <div>
              <h3 className="font-semibold text-slate-200 uppercase tracking-wide">
                Isolated Threat Quarantine Vault ({quarantineFiles.length} Items)
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Files stripped of execution privileges and held in restricted quarantine storage.
              </p>
            </div>
          </div>

          {quarantineFiles.length === 0 ? (
            <div className="py-16 text-center text-slate-500 font-mono">
              <ShieldCheck className="w-10 h-10 text-emerald-400/60 mx-auto mb-3" />
              <p className="text-sm font-semibold text-slate-300">Quarantine Vault Empty</p>
              <p className="text-xs text-slate-500 mt-1">No malicious files are currently isolated under containment.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] text-slate-400 uppercase tracking-wider">
                    <th className="py-3 px-4">File Name</th>
                    <th className="py-3 px-4">Original Path</th>
                    <th className="py-3 px-4">SHA-256 Fingerprint</th>
                    <th className="py-3 px-4">Owner</th>
                    <th className="py-3 px-4">Quarantined At</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {quarantineFiles.map((q: QuarantineFile) => (
                    <tr key={q.id} className="hover:bg-slate-900/50 transition-colors">
                      <td className="py-3 px-4 font-semibold text-slate-100 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Lock className="w-3.5 h-3.5 text-amber-400" />
                          <span>{q.file_name}</span>
                        </div>
                        <span className="text-[10px] text-slate-500 block">
                          Size: {formatBytes(q.file_size_bytes)}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-300 max-w-xs truncate" title={q.file_path}>
                        {q.file_path}
                      </td>
                      <td className="py-3 px-4 text-slate-400 font-mono text-[10px] max-w-[140px] truncate" title={q.sha256_hash}>
                        {q.sha256_hash}
                      </td>
                      <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                        {q.owner_name}
                      </td>
                      <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                        {new Date(q.quarantined_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-950 text-amber-300 border border-amber-700/50">
                          {q.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => restoreQuarantineMutation.mutate(q.id)}
                            disabled={restoreQuarantineMutation.isPending}
                            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-500/30 text-[11px] font-semibold transition-colors flex items-center gap-1"
                            title="Verify and restore back to original path"
                          >
                            <RotateCcw className="w-3 h-3" />
                            Restore
                          </button>
                          <button
                            onClick={() => {
                              if (confirm('Permanently purge this malicious quarantined payload?')) {
                                deleteQuarantineMutation.mutate(q.id);
                              }
                            }}
                            disabled={deleteQuarantineMutation.isPending}
                            className="px-2.5 py-1 rounded bg-red-950 hover:bg-red-900 text-red-300 border border-red-700/50 text-[11px] font-semibold transition-colors flex items-center gap-1"
                            title="Permanently delete payload"
                          >
                            <Trash2 className="w-3 h-3" />
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Threat Logs & Forensics */}
      {activeTab === 'logs' && (
        <div className="cyber-card rounded-xl border border-slate-800 overflow-hidden font-mono text-xs space-y-4 p-4">
          {/* Filter Bar */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
            <div className="flex flex-wrap items-center gap-3">
              {/* Timeframe Filter */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-slate-400">Timeframe:</span>
                <select
                  value={logTimeframe}
                  onChange={(e) => setLogTimeframe(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-slate-100 rounded px-2 py-1 text-xs focus:outline-none focus:border-cyan-500 cursor-pointer"
                >
                  <option value="all">All Time</option>
                  <option value="today">Today</option>
                  <option value="7days">Last 7 Days</option>
                  <option value="30days">Last 30 Days</option>
                </select>
              </div>

              {/* Severity Filter */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-slate-400">Severity:</span>
                <select
                  value={logSeverity}
                  onChange={(e) => setLogSeverity(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-slate-100 rounded px-2 py-1 text-xs focus:outline-none focus:border-cyan-500 cursor-pointer"
                >
                  <option value="ALL">All Severities</option>
                  <option value="CRITICAL">Critical</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>
              </div>
            </div>

            {/* Search Input */}
            <div className="relative w-full md:w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search threat actions or paths..."
                value={logSearch}
                onChange={(e) => setLogSearch(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 text-slate-100 rounded pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:border-cyan-500 placeholder:text-slate-500"
              />
            </div>
          </div>

          {/* Logs Table */}
          {threatLogs.length === 0 ? (
            <div className="py-12 text-center text-slate-500 font-mono">
              <FileWarning className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p>No threat forensic logs matching the current filter criteria.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] text-slate-400 uppercase tracking-wider">
                    <th className="py-2.5 px-3">Timestamp (UTC)</th>
                    <th className="py-2.5 px-3">Severity</th>
                    <th className="py-2.5 px-3">Threat Type</th>
                    <th className="py-2.5 px-3">Action</th>
                    <th className="py-2.5 px-3">File Path</th>
                    <th className="py-2.5 px-3">Forensic Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {threatLogs.map((log: ThreatLog) => (
                    <tr key={log.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-2.5 px-3 text-slate-400 whitespace-nowrap">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            log.severity === 'CRITICAL'
                              ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                              : log.severity === 'HIGH'
                              ? 'bg-orange-500/20 text-orange-300 border border-orange-500/40'
                              : log.severity === 'MEDIUM'
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                              : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                          }`}
                        >
                          {log.severity}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-slate-200 whitespace-nowrap">
                        {log.threat_type}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 whitespace-nowrap">
                        {log.action}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400 max-w-xs truncate" title={log.file_path || 'N/A'}>
                        {log.file_path || 'N/A'}
                      </td>
                      <td className="py-2.5 px-3 text-slate-500 text-[10px] max-w-xs truncate">
                        {log.details ? JSON.stringify(log.details) : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Clean Version Recovery Integration */}
      {activeTab === 'recovery' && (
        <div className="cyber-card p-6 rounded-xl border border-slate-800 font-mono text-xs space-y-6">
          <div className="border-b border-slate-800/80 pb-4">
            <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide flex items-center gap-2">
              <RotateCcw className="w-4 h-4 text-cyan-400" />
              Ransomware Clean-Point Recovery Recommendations
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Roll back attacked files or entire directory trees to verified pre-infection immutable snapshots with zero data loss.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg border border-cyan-500/30 bg-cyan-950/20 space-y-3">
              <div className="flex items-center gap-2 text-cyan-300 font-semibold">
                <FileCheck2 className="w-4 h-4" />
                <span>Single File Rollback</span>
              </div>
              <p className="text-[11px] text-slate-300">
                Restore the latest clean version backed up before the ransomware anomaly was detected.
              </p>
              <button
                onClick={() => navigate('/recovery')}
                className="w-full py-2 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold transition-colors flex items-center justify-center gap-2"
              >
                <span>Select Clean File &rarr;</span>
              </button>
            </div>

            <div className="p-4 rounded-lg border border-slate-800 bg-slate-900/60 space-y-3">
              <div className="flex items-center gap-2 text-slate-200 font-semibold">
                <FolderLock className="w-4 h-4 text-cyan-400" />
                <span>Protected Folder Rollback</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Restore entire compromised directories to the designated Safe Vault folder with directory hierarchy preserved.
              </p>
              <button
                onClick={() => navigate('/recovery')}
                className="w-full py-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold transition-colors flex items-center justify-center gap-2"
              >
                <span>Restore Folder &rarr;</span>
              </button>
            </div>

            <div className="p-4 rounded-lg border border-slate-800 bg-slate-900/60 space-y-3">
              <div className="flex items-center gap-2 text-slate-200 font-semibold">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>Point-in-Time Fleet Recovery</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Recover host state to the exact second prior to initial attack infiltration across all files.
              </p>
              <button
                onClick={() => navigate('/recovery')}
                className="w-full py-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold transition-colors flex items-center justify-center gap-2"
              >
                <span>Launch Point-in-Time &rarr;</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
