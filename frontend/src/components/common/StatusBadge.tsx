import React from 'react';

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const normalized = status.toUpperCase();

  const getStyle = () => {
    switch (normalized) {
      case 'ONLINE':
      case 'HEALTHY':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'OFFLINE':
      case 'UNHEALTHY':
      case 'REVOKED':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'DEGRADED':
      case 'PENDING':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      default:
        return 'bg-slate-700/30 text-slate-400 border-slate-600/30';
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border ${getStyle()}`}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current animate-pulse" />
      {normalized}
    </span>
  );
};

