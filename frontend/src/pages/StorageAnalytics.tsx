import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PieChart, HardDrive, TrendingDown, Layers, Laptop, RefreshCw } from 'lucide-react';
import { storageService } from '../services/storageService';
import { MetricCard } from '../components/widgets/MetricCard';

export const StorageAnalytics: React.FC = () => {
  const { data: stats, isLoading, refetch } = useQuery({
    queryKey: ['storage-statistics'],
    queryFn: storageService.getStorageStatistics,
    refetchInterval: 15000,
  });

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  const origBytes = stats?.total_original_bytes ?? 0;
  const storedBytes = stats?.total_stored_bytes ?? 0;
  const savedBytes = stats?.space_saved_bytes ?? 0;
  const savingsPct = stats?.compression_savings_percent ?? 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <PieChart className="w-5 h-5 text-cyan-400" />
            STORAGE ANALYTICS & COMPRESSION TELEMETRY
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            MinIO S3 storage consumption, compression savings ratios, and fleet endpoint volume distribution
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors self-start sm:self-auto"
          title="Refresh Analytics"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Stored Volume"
          value={isLoading ? '—' : formatBytes(storedBytes)}
          subtitle="Encrypted payload size"
          icon={HardDrive}
          variant="cyan"
        />
        <MetricCard
          title="Raw Uncompressed"
          value={isLoading ? '—' : formatBytes(origBytes)}
          subtitle="Original client volume"
          icon={Layers}
          variant="cyan"
        />
        <MetricCard
          title="Storage Saved"
          value={isLoading ? '—' : formatBytes(savedBytes)}
          subtitle={`${savingsPct}% savings via zlib`}
          icon={TrendingDown}
          variant="emerald"
        />
        <MetricCard
          title="Protected Folders"
          value={isLoading ? '—' : (stats?.active_protected_folders ?? 0)}
          subtitle="Monitored filesystem roots"
          icon={HardDrive}
          variant="emerald"
        />
      </div>

      {/* Efficiency Bar */}
      <div className="cyber-card p-6">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <h3 className="text-sm font-semibold text-slate-100 font-mono">
            Compression & Storage Efficiency Index
          </h3>
          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
            {savingsPct}% Bandwidth & Storage Reduction
          </span>
        </div>

        <div className="space-y-2">
          <div className="w-full bg-slate-900 h-4 rounded-full overflow-hidden p-0.5 border border-slate-800">
            <div
              className="bg-gradient-to-r from-cyan-500 to-emerald-400 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(5, 100 - savingsPct))}%` }}
            />
          </div>
          <div className="flex justify-between text-[11px] font-mono text-slate-400">
            <span>Stored Payload: {formatBytes(storedBytes)}</span>
            <span>Raw Dataset: {formatBytes(origBytes)}</span>
          </div>
        </div>
      </div>

      {/* Device Storage Usage Table */}
      <div className="cyber-card overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800">
          <h3 className="text-sm font-semibold text-slate-200 font-mono flex items-center gap-2">
            <Laptop className="w-4 h-4 text-cyan-400" />
            Device Storage Distribution Breakdown
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/40 text-slate-400 font-mono">
                <th className="py-3 px-4 font-medium">Device Name</th>
                <th className="py-3 px-4 font-medium">Device ID</th>
                <th className="py-3 px-4 font-medium">Unique Files</th>
                <th className="py-3 px-4 font-medium">Total Versions</th>
                <th className="py-3 px-4 font-medium">MinIO Storage Consumed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    Calculating storage statistics across fleet...
                  </td>
                </tr>
              ) : (stats?.device_breakdown ?? []).length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    No device storage metrics recorded yet.
                  </td>
                </tr>
              ) : (
                stats?.device_breakdown.map((dev) => (
                  <tr key={dev.device_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-slate-200">{dev.device_name}</td>
                    <td className="py-3.5 px-4 text-slate-400 truncate max-w-[140px]">{dev.device_id}</td>
                    <td className="py-3.5 px-4 text-slate-300 font-bold">{dev.total_files}</td>
                    <td className="py-3.5 px-4 text-cyan-400 font-bold">{dev.total_versions}</td>
                    <td className="py-3.5 px-4 text-emerald-400 font-bold">{formatBytes(dev.total_bytes)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

