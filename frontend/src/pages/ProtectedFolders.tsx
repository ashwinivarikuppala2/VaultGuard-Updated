import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FolderLock, Plus, Trash2, RefreshCw, AlertCircle } from 'lucide-react';
import { backupService } from '../services/backupService';
import { deviceService } from '../services/deviceService';
import { useToast } from '../contexts/ToastContext';
import { Modal } from '../components/common/Modal';

export const ProtectedFolders: React.FC = () => {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [folderPath, setFolderPath] = useState('');
  const [scanInterval, setScanInterval] = useState(300);
  const [includePatterns, setIncludePatterns] = useState('*.*');
  const [excludePatterns, setExcludePatterns] = useState('*.tmp,*.log,*.lock');
  const [error, setError] = useState<string | null>(null);

  const { data: folders, isLoading, refetch } = useQuery({
    queryKey: ['protected-folders'],
    queryFn: () => backupService.listProtectedFolders(),
  });

  const { data: devicesData } = useQuery({
    queryKey: ['devices-options'],
    queryFn: () => deviceService.list(undefined, 0, 100),
  });

  const createMutation = useMutation({
    mutationFn: backupService.createProtectedFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['protected-folders'] });
      queryClient.invalidateQueries({ queryKey: ['personal-folders'] });
      setIsModalOpen(false);
      setFolderPath('');
      setError(null);
      showToast('✓ Protected Folder Configured');
    },
    onError: (err: any) => {
      setError(err.response?.data?.error?.message || 'Failed to add protected folder.');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: backupService.deleteProtectedFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['protected-folders'] });
      queryClient.invalidateQueries({ queryKey: ['personal-folders'] });
      showToast('✓ Protected Folder Removed', 'info');
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDevice) {
      setError('Please select a target device.');
      return;
    }
    createMutation.mutate({
      device_id: selectedDevice,
      folder_path: folderPath,
      scan_interval_seconds: scanInterval,
      include_patterns: includePatterns,
      exclude_patterns: excludePatterns,
    });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <FolderLock className="w-5 h-5 text-cyan-400" />
            PROTECTED MONITORED DIRECTORIES
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Filesystem folders continuously watched by the VaultGuard Agent for automated encrypted backups
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            title="Refresh Folders"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold font-mono transition-colors shadow-lg shadow-cyan-950/40"
          >
            <Plus className="w-4 h-4" />
            <span>Add Protected Folder</span>
          </button>
        </div>
      </div>

      <div className="cyber-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/40 text-slate-400 font-mono">
                <th className="py-3 px-4 font-medium">Directory Path</th>
                <th className="py-3 px-4 font-medium">Target Device</th>
                <th className="py-3 px-4 font-medium">Sweep Interval</th>
                <th className="py-3 px-4 font-medium">Include Filter</th>
                <th className="py-3 px-4 font-medium">Exclude Filter</th>
                <th className="py-3 px-4 font-medium">Status</th>
                <th className="py-3 px-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    Scanning protected folder registry...
                  </td>
                </tr>
              ) : (folders ?? []).length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No protected directories enrolled. Click "Add Protected Folder" to configure a directory.
                  </td>
                </tr>
              ) : (
                folders?.map((folder) => {
                  const device = devicesData?.items.find((d) => d.id === folder.device_id);
                  return (
                    <tr key={folder.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-slate-200 flex items-center gap-2">
                        <FolderLock className="w-4 h-4 text-cyan-400" />
                        <span>{folder.folder_path}</span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-300">
                        {device ? device.name : folder.device_id.substring(0, 8)}
                      </td>
                      <td className="py-3.5 px-4 text-cyan-400 font-bold">
                        {folder.scan_interval_seconds}s
                      </td>
                      <td className="py-3.5 px-4 text-slate-400">{folder.include_patterns}</td>
                      <td className="py-3.5 px-4 text-slate-500">{folder.exclude_patterns}</td>
                      <td className="py-3.5 px-4">
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[11px]">
                          ACTIVE WATCH
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => deleteMutation.mutate(folder.id)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                          title="Remove from protection"
                        >
                          <Trash2 className="w-4 h-4" />
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

      {/* Add Protected Folder Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Configure Protected Directory">
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">Target Device</label>
            <select
              value={selectedDevice}
              onChange={(e) => setSelectedDevice(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value="">Select Enrolled Device...</option>
              {devicesData?.items.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.device_id})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">Folder Path on Device</label>
            <input
              type="text"
              required
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              placeholder="e.g. C:\Users\Finance\Documents or /var/data/confidential"
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">Scan Interval (Sec)</label>
              <input
                type="number"
                min={10}
                max={86400}
                required
                value={scanInterval}
                onChange={(e) => setScanInterval(parseInt(e.target.value, 10))}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">Include Patterns</label>
              <input
                type="text"
                required
                value={includePatterns}
                onChange={(e) => setIncludePatterns(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">Exclude Patterns</label>
            <input
              type="text"
              required
              value={excludePatterns}
              onChange={(e) => setExcludePatterns(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-mono transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-xs font-semibold font-mono text-white transition-colors"
            >
              {createMutation.isPending ? 'Configuring...' : 'Protect Directory'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

