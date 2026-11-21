import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  PieChart,
  BarChart3,
  TrendingUp,
  Radio,
  ShieldAlert,
  RefreshCw,
} from 'lucide-react';
import { threatService } from '../services/threatService';

export const ThreatAnalytics: React.FC = () => {
  const { data: analytics, isLoading, refetch } = useQuery({
    queryKey: ['threat-analytics-page'],
    queryFn: threatService.getThreatAnalytics,
    refetchInterval: 10000,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-purple-400" />
            ENTERPRISE THREAT ANALYTICS & ATTACK VECTORS
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Multi-Signal Correlation • MITRE ATT&CK Mapping • Canary Decoy Integrity
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono rounded bg-slate-900 border border-slate-800 text-slate-300 hover:text-slate-100 hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh Analytics
        </button>
      </div>

      {/* Grid: 2 columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 font-mono text-xs">
        {/* Threat Distribution Breakdown */}
        <div className="p-5 rounded-lg bg-slate-900/60 border border-slate-800 space-y-4">
          <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <PieChart className="w-4 h-4 text-cyan-400" />
            THREAT SIGNATURE & HEURISTIC BREAKDOWN
          </h2>

          <div className="space-y-3">
            {analytics?.threat_distribution && analytics.threat_distribution.length > 0 ? (
              analytics.threat_distribution.map((t, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-slate-300">
                    <span className="font-semibold">{t.name}</span>
                    <span className="text-cyan-400">{t.count} incidents</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-950 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-500 to-red-500 rounded-full"
                      style={{
                        width: `${Math.min(
                          100,
                          Math.max(10, (t.count / Math.max(1, analytics.total_detections)) * 100)
                        )}%`,
                      }}
                    ></div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-slate-500 py-6 text-center">No threat signatures currently active.</p>
            )}
          </div>
        </div>

        {/* 7-Day Timeline */}
        <div className="p-5 rounded-lg bg-slate-900/60 border border-slate-800 space-y-4">
          <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-emerald-400" />
            7-DAY DETECTION ACTIVITY TIMELINE
          </h2>

          <div className="grid grid-cols-7 gap-2 h-44 items-end pt-4 pb-2 border-b border-slate-800">
            {analytics?.timeline?.map((day, idx) => {
              const maxCount = Math.max(
                1,
                ...analytics.timeline.map((d) => d.detections)
              );
              const heightPct = Math.max(12, (day.detections / maxCount) * 100);

              return (
                <div key={idx} className="flex flex-col items-center gap-2 h-full justify-end">
                  <span className="text-[10px] text-slate-400 font-bold">{day.detections}</span>
                  <div
                    className={`w-full rounded-t transition-all ${
                      day.detections > 0 ? 'bg-red-500' : 'bg-slate-800'
                    }`}
                    style={{ height: `${heightPct}%` }}
                  ></div>
                  <span className="text-[9px] text-slate-500 whitespace-nowrap">
                    {day.date.slice(5)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Canary Decoys Health Status */}
        <div className="p-5 rounded-lg bg-slate-900/60 border border-slate-800 space-y-4">
          <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <Radio className="w-4 h-4 text-purple-400" />
            CANARY TRIPWIRE DEPLOYMENT POSTURE
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded bg-slate-950 border border-slate-800 text-center space-y-1">
              <span className="text-slate-400 text-[11px]">Deployed Decoys</span>
              <div className="text-2xl font-bold text-slate-100">
                {analytics?.canaries_deployed ?? 0}
              </div>
              <p className="text-[10px] text-slate-500">Continuous background polling</p>
            </div>

            <div className="p-4 rounded bg-slate-950 border border-slate-800 text-center space-y-1">
              <span className="text-slate-400 text-[11px]">Decoys Tripped</span>
              <div className={`text-2xl font-bold ${analytics?.canaries_tripped ? 'text-red-400' : 'text-emerald-400'}`}>
                {analytics?.canaries_tripped ?? 0}
              </div>
              <p className="text-[10px] text-slate-500">
                {analytics?.canaries_tripped ? 'Immediate containment active' : 'All tripwires intact'}
              </p>
            </div>
          </div>
        </div>

        {/* Alert Severity Distribution */}
        <div className="p-5 rounded-lg bg-slate-900/60 border border-slate-800 space-y-4">
          <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            ALERT SEVERITY DISTRIBUTION
          </h2>

          <div className="grid grid-cols-4 gap-2">
            <div className="p-3 rounded bg-slate-950 border border-red-900/40 text-center">
              <span className="text-red-400 text-[10px] uppercase font-bold">Critical</span>
              <div className="text-lg font-bold text-red-300 mt-1">
                {analytics?.alerts_by_severity?.CRITICAL ?? 0}
              </div>
            </div>
            <div className="p-3 rounded bg-slate-950 border border-amber-900/40 text-center">
              <span className="text-amber-400 text-[10px] uppercase font-bold">High</span>
              <div className="text-lg font-bold text-amber-300 mt-1">
                {analytics?.alerts_by_severity?.HIGH ?? 0}
              </div>
            </div>
            <div className="p-3 rounded bg-slate-950 border border-cyan-900/40 text-center">
              <span className="text-cyan-400 text-[10px] uppercase font-bold">Medium</span>
              <div className="text-lg font-bold text-cyan-300 mt-1">
                {analytics?.alerts_by_severity?.MEDIUM ?? 0}
              </div>
            </div>
            <div className="p-3 rounded bg-slate-950 border border-slate-800 text-center">
              <span className="text-slate-400 text-[10px] uppercase font-bold">Low</span>
              <div className="text-lg font-bold text-slate-300 mt-1">
                {analytics?.alerts_by_severity?.LOW ?? 0}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

