import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: string;
  variant?: 'cyan' | 'emerald' | 'amber' | 'crimson';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  variant = 'cyan',
}) => {
  const colorMap = {
    cyan: {
      border: 'hover:border-cyan-500/40',
      iconBg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
      badge: 'text-cyan-400 bg-cyan-500/10',
    },
    emerald: {
      border: 'hover:border-emerald-500/40',
      iconBg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      badge: 'text-emerald-400 bg-emerald-500/10',
    },
    amber: {
      border: 'hover:border-amber-500/40',
      iconBg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      badge: 'text-amber-400 bg-amber-500/10',
    },
    crimson: {
      border: 'hover:border-red-500/40',
      iconBg: 'bg-red-500/10 text-red-400 border-red-500/20',
      badge: 'text-red-400 bg-red-500/10',
    },
  };

  const colors = colorMap[variant];

  return (
    <div className={`cyber-card p-5 ${colors.border}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-mono tracking-wider text-slate-300 uppercase">{title}</p>
          <h3 className="text-2xl font-bold text-slate-100 mt-1 font-mono">{value}</h3>
          {subtitle && <p className="text-xs text-slate-300 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-xl border ${colors.iconBg}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      {trend && (
        <div className="mt-3 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
          <span className="text-slate-300">Status</span>
          <span className={`font-mono px-2 py-0.5 rounded ${colors.badge}`}>{trend}</span>
        </div>
      )}
    </div>
  );
};

