import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  Play,
  CheckCircle2,
  XCircle,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { backupService } from '../services/backupService';
import { deviceService } from '../services/deviceService';
import { StatusBadge } from '../components/common/StatusBadge';
import { Modal } from '../components/common/Modal';
import { useAuth } from '../hooks/useAuth';

export const BackupJobs: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role?.name === 'ADMIN';
  const [isStartModalOpen, setIsStartModalOpen] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [jobType, setJobType] = useState<'FULL' | 'INCREMENTAL'>('FULL');
  const [error, setError] = useState<string | null>(null);

  const { data: jobsData, isLoading, refetch } = useQuery({
    queryKey: ['backup-jobs'],
    queryFn: () => backupService.listJobs(undefined, undefined, 0, 50),
    refetchInterval: 5000,
  });

  const { data: devicesData } = useQuery({
    queryKey: ['devices-options'],
    queryFn: () => deviceService.list(undefined, 0, 100),
  });
  const backupDevices = (devicesData?.items ?? []).filter(
    (device) => !isAdmin || device.user_id === user?.id
  );

  const startJobMutation = useMutation({
    mutationFn: (data: { device_id: string; job_type: 'FULL' | 'INCREMENTAL' }) =>
      backupService.startBackup(data.device_id, undefined, data.job_type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backup-jobs'] });
      setIsStartModalOpen(false);
      setError(null);
    },
    onError: (err: any) => {
      setError(err.response?.data?.error?.message || 'Failed to start backup job.');
    },
  });

  const handleStartJob = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDevice) {
      setError('Please select an enrolled device.');
      return;
    }
    startJobMutation.mutate({
      device_id: selectedDevice,
      job_type: jobType,
    });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            BACKUP EXECUTION JOBS
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time status queue of scheduled, continuous, and manual backup operations
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            title="Refresh Jobs"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsStartModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold font-mono transition-colors shadow-lg shadow-cyan-950/40"
          >
            <Play className="w-4 h-4" />
            <span>Trigger Backup Job</span>
          </button>
        </div>
      </div>

      <div className="cyber-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/40 text-slate-400 font-mono">
                <th className="py-3 px-4 font-medium">Job Identifier</th>
                <th className="py-3 px-4 font-medium">Type</th>
                <th className="py-3 px-4 font-medium">Status</th>
                <th className="py-3 px-4 font-medium">Files Processed</th>
                <th className="py-3 px-4 font-medium">Volume</th>
                <th className="py-3 px-4 font-medium">Duration</th>
                <th className="py-3 px-4 font-medium">Started At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    Loading backup job telemetry...
                  </td>
                </tr>
              ) : (jobsData?.items ?? []).length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No backup jobs recorded. Click "Trigger Backup Job" to initiate a run.
                  </td>
                </tr>
              ) : (
                jobsData?.items.map((job) => {
                  let badge = <StatusBadge status={job.status} />;
                  if (job.status === 'COMPLETED') {
                    badge = (
                      <span className="inline-flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
                        <CheckCircle2 className="w-3.5 h-3.5" /> COMPLETED
                      </span>
                    );
                  } else if (job.status === 'FAILED') {
                    badge = (
                      <span className="inline-flex items-center gap-1 text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/30">
                        <XCircle className="w-3.5 h-3.5" /> FAILED
                      </span>
                    );
                  }

                  return (
                    <tr key={job.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4 font-bold text-cyan-400 truncate max-w-[140px]" title={job.id}>
                        {job.id.substring(0, 8)}...
                      </td>
                      <td className="py-3 px-4 text-slate-200">
                        <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-[11px]">
                          {job.job_type}
                        </span>
                      </td>
                      <td className="py-3 px-4">{badge}</td>
                      <td className="py-3 px-4 text-slate-300">
                        <span className="text-cyan-400 font-bold">{job.total_files}</span> files
                        {job.files_failed > 0 && (
                          <span className="text-red-400 ml-1.5">({job.files_failed} failed)</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        {(job.bytes_processed / 1024).toFixed(1)} KB
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {job.duration_seconds > 0 ? `${job.duration_seconds}s` : 'Active'}
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {job.started_at ? new Date(job.started_at).toLocaleTimeString() : 'Pending'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Start Backup Modal */}
      <Modal isOpen={isStartModalOpen} onClose={() => setIsStartModalOpen(false)} title="Trigger Backup Execution Run">
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <form onSubmit={handleStartJob} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">Target Device</label>
            <select
              value={selectedDevice}
              onChange={(e) => setSelectedDevice(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value="">Select Enrolled Device...</option>
              {backupDevices.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.device_id})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">Backup Strategy</label>
            <select
              value={jobType}
              onChange={(e) => setJobType(e.target.value as any)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value="FULL">FULL (Complete snapshot sweep)</option>
              <option value="INCREMENTAL">INCREMENTAL (Changes since last snapshot)</option>
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setIsStartModalOpen(false)}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-mono transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={startJobMutation.isPending}
              className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-xs font-semibold font-mono text-white transition-colors"
            >
              {startJobMutation.isPending ? 'Queuing Job...' : 'Dispatch Job'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

