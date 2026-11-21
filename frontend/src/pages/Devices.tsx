import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { HardDrive, Plus, Laptop, Server, AlertCircle, RefreshCw } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../contexts/ToastContext';
import { deviceService } from '../services/deviceService';
import { DeviceStatus } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { Modal } from '../components/common/Modal';

export const Devices: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { showToast } = useToast();

  const isIndividual = user?.role?.name === 'INDIVIDUAL';
  const isAdmin = user?.role?.name === 'ADMIN';

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [deviceId, setDeviceId] = useState('');
  const [name, setName] = useState('');
  const [os, setOs] = useState('Windows 11 Enterprise');
  const [statusFilter, setStatusFilter] = useState<DeviceStatus | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['devices-list', statusFilter],
    queryFn: () => deviceService.list(statusFilter, 0, 100),
  });

  const registerMutation = useMutation({
    mutationFn: deviceService.register,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices-list'] });
      queryClient.invalidateQueries({ queryKey: ['devices-count'] });
      queryClient.invalidateQueries({ queryKey: ['personal-devices'] });
      queryClient.invalidateQueries({ queryKey: ['employee-devices'] });
      queryClient.invalidateQueries({ queryKey: ['admin-devices'] });
      setIsModalOpen(false);
      setDeviceId('');
      setName('');
      setError(null);
      showToast('✓ Device Registered');
    },
    onError: (err: any) => {
      setError(err.response?.data?.error?.message || 'Failed to register device.');
    },
  });

  const handleRegisterDevice = (e: React.FormEvent) => {
    e.preventDefault();
    if (registerMutation.isPending) return;
    setError(null);
    registerMutation.mutate({
      device_id: deviceId.trim(),
      name: name.trim(),
      os,
    });
  };

  const isServer = (deviceOs: string) =>
    deviceOs.toLowerCase().includes('server') || deviceOs.toLowerCase().includes('linux');

  // Terminology adaptations
  const pageTitle = isIndividual
    ? 'MY PROTECTED WORKSTATIONS & DEVICES'
    : isAdmin
    ? 'ORGANIZATION FLEET ENDPOINTS & SERVERS'
    : 'MY ASSIGNED WORKSTATION';

  const pageSubtitle = isIndividual
    ? 'Register and monitor your personal laptop or desktop for ransomware protection and cloud backup'
    : isAdmin
    ? 'Enterprise fleet devices enrolled for ransomware defense and automated cloud backups'
    : 'Your workstation connected to VaultGuard cloud backup protection';

  const enrollButtonLabel = isIndividual
    ? 'Register My Device'
    : isAdmin
    ? 'Enroll Organization Device'
    : 'Register My Device';

  const modalTitle = isIndividual
    ? 'Register My Device'
    : isAdmin
    ? 'Enroll Organization Device'
    : 'Register My Device';

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <HardDrive className="w-5 h-5 text-cyan-400" />
            <span>{pageTitle}</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">{pageSubtitle}</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            title="Refresh Devices"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold font-mono transition-colors shadow-lg shadow-cyan-950/40"
          >
            <Plus className="w-4 h-4" />
            <span>{enrollButtonLabel}</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center space-x-2 text-xs font-mono">
        <button
          onClick={() => setStatusFilter(undefined)}
          className={`px-3 py-1.5 rounded-lg border transition-colors ${
            statusFilter === undefined
              ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-400'
              : 'border-slate-800 text-slate-400 hover:text-slate-200'
          }`}
        >
          All Devices
        </button>
        <button
          onClick={() => setStatusFilter('ONLINE')}
          className={`px-3 py-1.5 rounded-lg border transition-colors ${
            statusFilter === 'ONLINE'
              ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400'
              : 'border-slate-800 text-slate-400 hover:text-slate-200'
          }`}
        >
          Online Only
        </button>
        <button
          onClick={() => setStatusFilter('OFFLINE')}
          className={`px-3 py-1.5 rounded-lg border transition-colors ${
            statusFilter === 'OFFLINE'
              ? 'bg-amber-500/10 border-amber-500/40 text-amber-400'
              : 'border-slate-800 text-slate-400 hover:text-slate-200'
          }`}
        >
          Offline
        </button>
        <button
          onClick={() => setStatusFilter('QUARANTINED')}
          className={`px-3 py-1.5 rounded-lg border transition-colors ${
            statusFilter === 'QUARANTINED'
              ? 'bg-red-500/10 border-red-500/40 text-red-400'
              : 'border-slate-800 text-slate-400 hover:text-slate-200'
          }`}
        >
          Quarantined
        </button>
      </div>

      {/* Devices Table */}
      <div className="cyber-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 font-mono">
                <th className="py-3 px-4 font-medium">Device Identifier</th>
                <th className="py-3 px-4 font-medium">Friendly Name</th>
                <th className="py-3 px-4 font-medium">Operating System</th>
                <th className="py-3 px-4 font-medium">Status</th>
                <th className="py-3 px-4 font-medium">Last Seen</th>
                <th className="py-3 px-4 font-medium">Enrolled Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    <span className="inline-block w-5 h-5 border-2 border-cyan-400/20 border-t-cyan-400 rounded-full animate-spin mr-2" />
                    Querying device telemetry...
                  </td>
                </tr>
              ) : data?.items?.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No devices registered yet.{' '}
                    <button
                      onClick={() => setIsModalOpen(true)}
                      className="text-cyan-400 hover:underline ml-1 font-semibold"
                    >
                      {enrollButtonLabel}
                    </button>
                  </td>
                </tr>
              ) : (
                data?.items?.map((dev) => (
                  <tr key={dev.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-slate-200 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-cyan-400" />
                      {dev.device_id}
                    </td>
                    <td className="py-3.5 px-4 text-slate-200 flex items-center gap-2">
                      {isServer(dev.os) ? (
                        <Server className="w-4 h-4 text-slate-400" />
                      ) : (
                        <Laptop className="w-4 h-4 text-slate-400" />
                      )}
                      {dev.name}
                    </td>
                    <td className="py-3.5 px-4 text-slate-300">{dev.os}</td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={dev.status} />
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">
                      {dev.last_seen ? new Date(dev.last_seen).toLocaleTimeString() : 'Never'}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500">
                      {new Date(dev.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal: Enroll / Register Device */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={modalTitle}>
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2 font-mono">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <form onSubmit={handleRegisterDevice} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">
              {isIndividual ? 'Device Tag / Identifier' : 'Device ID (Unique Tag)'}
            </label>
            <input
              type="text"
              required
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value.toUpperCase())}
              placeholder={isIndividual ? 'e.g. MY-LAPTOP-01' : 'e.g. ENDPOINT-SEC-042'}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">
              {isIndividual ? 'My Device Name' : 'Friendly Name'}
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={isIndividual ? 'e.g. MacBook Pro Workstation' : 'e.g. Chief Risk Officer Laptop'}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1 uppercase">Operating System</label>
            <select
              value={os}
              onChange={(e) => setOs(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value="Windows 11 Enterprise">Windows 11 / 10</option>
              <option value="Windows Server 2022">Windows Server</option>
              <option value="macOS Sonoma 14.5">macOS</option>
              <option value="Ubuntu 22.04 LTS Linux">Ubuntu / Debian Linux</option>
              <option value="Red Hat Enterprise Linux 9">RHEL / Fedora Linux</option>
            </select>
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
              disabled={registerMutation.isPending}
              className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-xs font-semibold font-mono text-white transition-colors flex items-center gap-2"
            >
              {registerMutation.isPending ? (
                <>
                  <span className="inline-block w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  <span>Registering...</span>
                </>
              ) : (
                <span>{isIndividual ? 'Register Device' : 'Enroll Device'}</span>
              )}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
