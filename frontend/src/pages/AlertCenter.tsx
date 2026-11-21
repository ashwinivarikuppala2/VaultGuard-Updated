import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Filter,
  RefreshCw,
  MessageSquare,
  CheckCheck,
} from 'lucide-react';
import { threatService } from '../services/threatService';
import { StatusBadge } from '../components/common/StatusBadge';
import { Alert } from '../types';

export const AlertCenter: React.FC = () => {
  const queryClient = useQueryClient();
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [activeModalAlert, setActiveModalAlert] = useState<{ alert: Alert; mode: 'ACK' | 'RESOLVE' } | null>(null);
  const [operatorNotes, setOperatorNotes] = useState<string>('');

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['alerts-list', severityFilter, statusFilter],
    queryFn: () =>
      threatService.getAlerts({
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
      }),
    refetchInterval: 5000,
  });

  const ackMutation = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      threatService.acknowledgeAlert(id, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts-list'] });
      queryClient.invalidateQueries({ queryKey: ['threat-analytics'] });
      setActiveModalAlert(null);
      setOperatorNotes('');
    },
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes: string }) =>
      threatService.resolveAlert(id, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts-list'] });
      queryClient.invalidateQueries({ queryKey: ['threat-analytics'] });
      setActiveModalAlert(null);
      setOperatorNotes('');
    },
  });

  const handleActionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeModalAlert) return;

    if (activeModalAlert.mode === 'ACK') {
      ackMutation.mutate({ id: activeModalAlert.alert.id, notes: operatorNotes });
    } else {
      resolveMutation.mutate({ id: activeModalAlert.alert.id, notes: operatorNotes || 'Mitigated' });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            SECURITY OPERATIONS ALERT CENTER
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Triage & Incident Remediation • Operator Accountability • SLA Tracking
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono rounded bg-slate-900 border border-slate-800 text-slate-300 hover:text-slate-100 hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh Alerts
        </button>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs font-mono">
        <Filter className="w-4 h-4 text-slate-500" />
        <span className="text-slate-400">Filter by:</span>

        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
        >
          <option value="">All Severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
        >
          <option value="">All Statuses</option>
          <option value="NEW">New (Unacknowledged)</option>
          <option value="ACKNOWLEDGED">Acknowledged</option>
          <option value="RESOLVED">Resolved</option>
        </select>
      </div>

      {/* Alerts List */}
      <div className="space-y-3">
        {data && data.items.length > 0 ? (
          data.items.map((alert) => (
            <div
              key={alert.id}
              className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4 font-mono text-xs"
            >
              <div className="space-y-1.5 max-w-2xl">
                <div className="flex items-center gap-2">
                  <StatusBadge status={alert.severity} />
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] ${
                      alert.status === 'NEW'
                        ? 'bg-red-950 text-red-400 border border-red-800 font-bold'
                        : alert.status === 'ACKNOWLEDGED'
                        ? 'bg-amber-950 text-amber-400 border border-amber-800'
                        : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    }`}
                  >
                    {alert.status}
                  </span>
                  <span className="text-slate-500 text-[11px]">
                    {new Date(alert.created_at).toLocaleString()}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-slate-100">{alert.title}</h3>
                <p className="text-slate-400 text-xs">{alert.description}</p>
                {alert.mitigation_notes && (
                  <p className="text-cyan-400 text-[11px]">Resolution notes: {alert.mitigation_notes}</p>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 shrink-0">
                {alert.status === 'NEW' && (
                  <button
                    onClick={() => setActiveModalAlert({ alert, mode: 'ACK' })}
                    className="px-3 py-1.5 rounded bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/40 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <Clock className="w-3.5 h-3.5" />
                    Acknowledge
                  </button>
                )}
                {alert.status !== 'RESOLVED' && (
                  <button
                    onClick={() => setActiveModalAlert({ alert, mode: 'RESOLVE' })}
                    className="px-3 py-1.5 rounded bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <CheckCheck className="w-3.5 h-3.5" />
                    Resolve
                  </button>
                )}
              </div>
            </div>
          ))
        ) : (
          <div className="p-12 text-center rounded-lg bg-slate-900/40 border border-slate-800 text-slate-500 font-mono text-xs">
            <CheckCircle className="w-8 h-8 text-emerald-500/50 mx-auto mb-2" />
            No alerts found. System threat levels are nominal.
          </div>
        )}
      </div>

      {/* Operator Action Modal */}
      {activeModalAlert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <form
            onSubmit={handleActionSubmit}
            className="bg-slate-900 border border-slate-800 rounded-lg max-w-md w-full p-6 space-y-4 font-mono text-xs"
          >
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-cyan-400" />
              {activeModalAlert.mode === 'ACK' ? 'Acknowledge Alert' : 'Mark Alert as Resolved'}
            </h3>
            <p className="text-slate-400">{activeModalAlert.alert.title}</p>

            <div>
              <label className="block text-slate-400 mb-1">Operator Notes / Mitigation Action:</label>
              <textarea
                value={operatorNotes}
                onChange={(e) => setOperatorNotes(e.target.value)}
                placeholder="Enter actions taken (e.g. host isolated, user notified, sandbox scan run)..."
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setActiveModalAlert(null)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={ackMutation.isPending || resolveMutation.isPending}
                className="px-3 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold"
              >
                {activeModalAlert.mode === 'ACK' ? 'Confirm Acknowledge' : 'Confirm Resolution'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

