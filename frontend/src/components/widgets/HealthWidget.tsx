import React from 'react';
import { Database, Server, HardDrive } from 'lucide-react';
import { SystemHealth } from '../../types';
import { StatusBadge } from '../common/StatusBadge';

interface HealthWidgetProps {
  health: SystemHealth | null;
  isLoading: boolean;
}

export const HealthWidget: React.FC<HealthWidgetProps> = ({ health, isLoading }) => {
  if (isLoading || !health) {
    return (
      <div className="cyber-card p-6 animate-pulse">
        <div className="h-4 bg-slate-800 rounded w-1/3 mb-4" />
        <div className="space-y-3">
          <div className="h-10 bg-slate-800/60 rounded" />
          <div className="h-10 bg-slate-800/60 rounded" />
          <div className="h-10 bg-slate-800/60 rounded" />
        </div>
      </div>
    );
  }

  const items = [
    {
      name: 'PostgreSQL Database',
      key: 'database',
      icon: Database,
      component: health.services.database,
    },
    {
      name: 'Redis Cache & Queue',
      key: 'redis',
      icon: Server,
      component: health.services.redis,
    },
    {
      name: 'MinIO Object Storage (S3)',
      key: 'minio',
      icon: HardDrive,
      component: health.services.minio,
    },
  ];

  return (
    <div className="cyber-card p-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            Infrastructure Telemetry & Health Probes
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time connection monitoring for core platform services
          </p>
        </div>
        <StatusBadge status={health.status} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {items.map((item) => {
          const Icon = item.icon;
          const status = item.component?.status || 'UNKNOWN';
          const latency = item.component?.latency_ms;
          const isHealthy = status === 'HEALTHY';

          return (
            <div
              key={item.key}
              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2.5">
                  <div
                    className={`p-2 rounded-lg border ${
                      isHealthy
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-red-500/10 text-red-400 border-red-500/20'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-200">{item.name}</h4>
                    <span className="text-[10px] font-mono text-slate-400">
                      {latency != null ? `${latency} ms` : 'Offline'}
                    </span>
                  </div>
                </div>
                <StatusBadge status={status} />
              </div>

              <div className="text-[11px] font-mono text-slate-400 truncate bg-slate-950/40 px-2.5 py-1.5 rounded border border-slate-800/60">
                {item.component?.details || 'Probed successfully'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

