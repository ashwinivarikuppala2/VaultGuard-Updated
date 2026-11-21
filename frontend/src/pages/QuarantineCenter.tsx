import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Lock,
  Unlock,
  ShieldAlert,
  RefreshCw,
  Plus,
  CheckCircle,
} from 'lucide-react';
import { threatService } from '../services/threatService';
import { deviceService } from '../services/deviceService';
import { Device } from '../types';

export const QuarantineCenter: React.FC = () => {
  const queryClient = useQueryClient();
  const [isQuarantineModalOpen, setIsQuarantineModalOpen] = useState(false);
  const [targetDeviceId, setTargetDeviceId] = useState('');
  const [reason, setReason] = useState('');
  const [suspectPid, setSuspectPid] = useState('');

  const { data: quarantineData, isLoading, refetch } = useQuery({
    queryKey: ['quarantine-events'],
    queryFn: () => threatService.getQuarantineEvents(),
    refetchInterval: 5000,
  });

  const { data: devicesData } = useQuery({
    queryKey: ['devices-for-quarantine'],
    queryFn: () => deviceService.list(),
  });

  const quarantineMutation = useMutation({
    mutationFn: ({ deviceId, r, pid }: { deviceId: string; r: string; pid?: number }) =>
      threatService.quarantineDevice(deviceId, r, pid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quarantine-events'] });
      queryClient.invalidateQueries({ queryKey: ['devices'] });
      queryClient.invalidateQueries({ queryKey: ['threat-analytics'] });
      setIsQuarantineModalOpen(false);
      setTargetDeviceId('');
      setReason('');
      setSuspectPid('');
    },
  });

  const releaseMutation = useMutation({
    mutationFn: (deviceId: string) => threatService.releaseDevice(deviceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quarantine-events'] });
      queryClient.invalidateQueries({ queryKey: ['devices'] });
      queryClient.invalidateQueries({ queryKey: ['threat-analytics'] });
    },
  });

  const handleQuarantineSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetDeviceId || !reason) return;
    quarantineMutation.mutate({
      deviceId: targetDeviceId,
      r: reason,
      pid: suspectPid ? parseInt(suspectPid, 10) : undefined,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <Lock className="w-5 h-5 text-red-500" />
            ENDPOINT & PAYLOAD QUARANTINE CENTER
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Host Network Isolation • Suspect Process Termination • Cloud Backup Freeze
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsQuarantineModalOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono font-semibold rounded bg-red-600 hover:bg-red-500 text-white transition-colors"
          >
            <Plus className="w-4 h-4" />
            Emergency Isolate Host
          </button>
          <button
            onClick={() => refetch()}
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Quarantine Events List */}
      <div className="rounded-lg bg-slate-900/60 border border-slate-800 overflow-hidden font-mono text-xs">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-red-400" />
            ISOLATION POLICIES & QUARANTINE AUDIT RECORDS
          </h2>
          <span className="text-slate-500 text-[11px]">
            {quarantineData?.items?.filter((i) => i.is_active).length ?? 0} currently isolated
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Target Device</th>
                <th className="py-3 px-4">Isolation Level</th>
                <th className="py-3 px-4">Reason & Trigger</th>
                <th className="py-3 px-4">Quarantined At</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {quarantineData && quarantineData.items.length > 0 ? (
                quarantineData.items.map((event) => (
                  <tr key={event.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4">
                      {event.is_active ? (
                        <span className="px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800 font-bold text-[10px] flex items-center gap-1 w-max">
                          <Lock className="w-3 h-3" />
                          ISOLATED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px] flex items-center gap-1 w-max">
                          <CheckCircle className="w-3 h-3" />
                          RELEASED
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-200 font-semibold">
                      {event.device_id || 'System Fleet'}
                    </td>
                    <td className="py-3 px-4 text-cyan-400">{event.isolation_level}</td>
                    <td className="py-3 px-4 text-slate-300 max-w-xs truncate" title={event.reason}>
                      {event.reason}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {new Date(event.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {event.is_active && event.device_id && (
                        <button
                          onClick={() => releaseMutation.mutate(event.device_id!)}
                          disabled={releaseMutation.isPending}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/40 text-[11px] font-semibold flex items-center gap-1 ml-auto transition-colors"
                        >
                          <Unlock className="w-3 h-3" />
                          Release Host
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    No active or historical quarantine records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manual Quarantine Modal */}
      {isQuarantineModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <form
            onSubmit={handleQuarantineSubmit}
            className="bg-slate-900 border border-slate-800 rounded-lg max-w-md w-full p-6 space-y-4 font-mono text-xs"
          >
            <h3 className="text-sm font-bold text-red-400 flex items-center gap-2">
              <Lock className="w-4 h-4" />
              Emergency Endpoint Isolation
            </h3>
            <p className="text-slate-400">
              Immediately severs network traffic from the endpoint and freezes cloud backup writes.
            </p>

            <div>
              <label className="block text-slate-400 mb-1">Select Target Endpoint:</label>
              <select
                value={targetDeviceId}
                onChange={(e) => setTargetDeviceId(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-red-500"
              >
                <option value="">-- Choose Device --</option>
                {devicesData?.items?.map((d: Device) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.device_id}) - {d.status}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Isolation Justification / Incident Details:</label>
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Hostile ransomware beacon detected by EDR"
                required
                className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-red-500"
              />
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Suspect Process ID (PID) to terminate (optional):</label>
              <input
                type="number"
                value={suspectPid}
                onChange={(e) => setSuspectPid(e.target.value)}
                placeholder="e.g. 4812"
                className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-red-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsQuarantineModalOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={quarantineMutation.isPending}
                className="px-3 py-1.5 rounded bg-red-600 hover:bg-red-500 text-white font-semibold"
              >
                Enforce Quarantine
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

