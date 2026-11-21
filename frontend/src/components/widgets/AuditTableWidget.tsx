import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { AuditLog } from '../../types';

interface AuditTableWidgetProps {
  logs: AuditLog[];
  isLoading: boolean;
}

export const AuditTableWidget: React.FC<AuditTableWidgetProps> = ({ logs, isLoading }) => {
  if (isLoading) {
    return (
      <div className="cyber-card p-6 animate-pulse">
        <div className="h-4 bg-slate-800 rounded w-1/4 mb-4" />
        <div className="space-y-3">
          <div className="h-8 bg-slate-800/40 rounded" />
          <div className="h-8 bg-slate-800/40 rounded" />
          <div className="h-8 bg-slate-800/40 rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="cyber-card p-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            Immutable Audit Log Activity
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Tamper-resistant audit trails capturing identity, mutations, and device enrollments
          </p>
        </div>
        <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2 py-1 rounded border border-cyan-500/20">
          {logs.length} Recent Entries
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 font-mono">
              <th className="pb-3 font-medium">Timestamp</th>
              <th className="pb-3 font-medium">Action</th>
              <th className="pb-3 font-medium">Target Entity</th>
              <th className="pb-3 font-medium">Resource ID</th>
              <th className="pb-3 font-medium">Client IP</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-6 text-center text-slate-500">
                  No audit log entries recorded yet.
                </td>
              </tr>
            ) : (
              logs.map((log) => {
                const isAuth = log.action.startsWith('AUTH');
                const isOrg = log.action.startsWith('ORG');
                const isDevice = log.action.startsWith('DEVICE');

                let badgeColor = 'bg-slate-700/20 text-slate-300 border-slate-600/30';
                if (isAuth) badgeColor = 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
                if (isOrg) badgeColor = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
                if (isDevice) badgeColor = 'bg-amber-500/10 text-amber-400 border-amber-500/30';

                return (
                  <tr key={log.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 text-slate-400 whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 rounded border text-[11px] ${badgeColor}`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3 text-slate-300">{log.resource_type}</td>
                    <td className="py-3 text-slate-400 truncate max-w-[150px]">
                      {log.resource_id || '—'}
                    </td>
                    <td className="py-3 text-slate-500">{log.ip_address || '127.0.0.1'}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

