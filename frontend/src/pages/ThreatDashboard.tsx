import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ShieldAlert,
  AlertTriangle,
  Radio,
  Lock,
  Flame,
  Activity,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';
import { threatService } from '../services/threatService';
import { StatusBadge } from '../components/common/StatusBadge';
import { NavLink } from 'react-router-dom';

export const ThreatDashboard: React.FC = () => {
  const { data: analytics, isLoading, refetch } = useQuery({
    queryKey: ['threat-analytics'],
    queryFn: threatService.getThreatAnalytics,
    refetchInterval: 5000,
  });

  const { data: recentThreats } = useQuery({
    queryKey: ['recent-threats'],
    queryFn: () => threatService.getThreats({ limit: 5 }),
    refetchInterval: 5000,
  });

  const avgRisk = analytics?.fleet_average_risk_score ?? 0;
  const isHighRisk = avgRisk >= 70;
  const isMedRisk = avgRisk >= 40 && avgRisk < 70;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-500" />
            ENTERPRISE THREAT & RANSOMWARE MONITOR
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Continuous Heuristic Scoring • Canary Tripwires • Automated Host Quarantine
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            ACTIVE HEURISTICS ENGINE
          </span>
          <button
            onClick={() => refetch()}
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded transition-colors"
            title="Refresh telemetry"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Critical Alert Banner if outbreaks active */}
      {analytics && analytics.active_detections > 0 && (
        <div className="p-4 rounded-lg bg-red-950/40 border border-red-500/40 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <Flame className="w-5 h-5 text-red-400 mt-0.5 animate-bounce" />
            <div>
              <h3 className="text-sm font-semibold text-red-200 font-mono">
                CRITICAL: ACTIVE RANSOMWARE OUTBREAK DETECTED
              </h3>
              <p className="text-xs text-red-300/80 mt-1">
                {analytics.active_detections} active threat incident(s) detected. Compromised endpoints have been isolated to protect cloud backups.
              </p>
            </div>
          </div>
          <NavLink
            to="/quarantine"
            className="px-3 py-1.5 rounded bg-red-600 hover:bg-red-500 text-white font-mono text-xs font-semibold whitespace-nowrap"
          >
            View Quarantine Center
          </NavLink>
        </div>
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Fleet Risk Level */}
        <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-mono uppercase tracking-wider">Fleet Threat Posture</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold font-mono ${
                isHighRisk ? 'text-red-400' : isMedRisk ? 'text-amber-400' : 'text-emerald-400'
              }`}
            >
              {avgRisk.toFixed(1)}
            </span>
            <span className="text-xs text-slate-500 font-mono">/ 100</span>
          </div>
          <p className="text-[11px] text-slate-400 font-mono">
            Status: {isHighRisk ? 'CRITICAL RISK' : isMedRisk ? 'ELEVATED RISK' : 'NORMAL SECURE'}
          </p>
        </div>

        {/* Quarantined Endpoints */}
        <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-mono uppercase tracking-wider">Quarantined Endpoints</span>
            <Lock className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {analytics?.quarantined_endpoints ?? 0}
          </div>
          <p className="text-[11px] text-slate-400 font-mono">
            {analytics?.quarantined_endpoints ? 'Hosts isolated from network' : 'Zero hosts currently isolated'}
          </p>
        </div>

        {/* Canary Decoys Tripped */}
        <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-mono uppercase tracking-wider">Canary Decoys</span>
            <Radio className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-bold font-mono ${analytics?.canaries_tripped ? 'text-red-400' : 'text-slate-100'}`}>
              {analytics?.canaries_tripped ?? 0}
            </span>
            <span className="text-xs text-slate-500 font-mono">
              / {analytics?.canaries_deployed ?? 0} tripped
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-mono">
            {analytics?.canaries_tripped ? 'Tripwire tamper detected!' : 'All decoy files uncompromised'}
          </p>
        </div>

        {/* Active SOC Alerts */}
        <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-mono uppercase tracking-wider">Active Alerts</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {(analytics?.alerts_by_severity?.CRITICAL ?? 0) + (analytics?.alerts_by_severity?.HIGH ?? 0) + (analytics?.alerts_by_severity?.MEDIUM ?? 0)}
          </div>
          <div className="flex gap-2 text-[10px] font-mono text-slate-400">
            <span className="text-red-400">{analytics?.alerts_by_severity?.CRITICAL ?? 0} Crit</span>
            <span className="text-amber-400">{analytics?.alerts_by_severity?.HIGH ?? 0} High</span>
            <span className="text-cyan-400">{analytics?.alerts_by_severity?.MEDIUM ?? 0} Med</span>
          </div>
        </div>
      </div>

      {/* Fast Navigation Quick Links */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        <NavLink
          to="/detections"
          className="p-3 rounded bg-slate-900/40 border border-slate-800 hover:border-cyan-500/40 transition-colors text-center"
        >
          <div className="text-xs font-mono font-semibold text-slate-200">Detections</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Inspect Signals</div>
        </NavLink>
        <NavLink
          to="/live-events"
          className="p-3 rounded bg-slate-900/40 border border-slate-800 hover:border-cyan-500/40 transition-colors text-center"
        >
          <div className="text-xs font-mono font-semibold text-slate-200">Live Telemetry</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Real-time Stream</div>
        </NavLink>
        <NavLink
          to="/alerts"
          className="p-3 rounded bg-slate-900/40 border border-slate-800 hover:border-cyan-500/40 transition-colors text-center"
        >
          <div className="text-xs font-mono font-semibold text-slate-200">Alert Center</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Triage & Resolve</div>
        </NavLink>
        <NavLink
          to="/quarantine"
          className="p-3 rounded bg-slate-900/40 border border-slate-800 hover:border-cyan-500/40 transition-colors text-center"
        >
          <div className="text-xs font-mono font-semibold text-slate-200">Quarantine</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Host Isolation</div>
        </NavLink>
        <NavLink
          to="/threat-analytics"
          className="p-3 rounded bg-slate-900/40 border border-slate-800 hover:border-cyan-500/40 transition-colors text-center"
        >
          <div className="text-xs font-mono font-semibold text-slate-200">Analytics</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Attack Vectors</div>
        </NavLink>
        <NavLink
          to="/risk-policies"
          className="p-3 rounded bg-slate-900/40 border border-slate-800 hover:border-cyan-500/40 transition-colors text-center"
        >
          <div className="text-xs font-mono font-semibold text-slate-200">Risk Policies</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Tune Weights</div>
        </NavLink>
      </div>

      {/* Recent Detections Table */}
      <div className="p-5 rounded-lg bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-100 font-mono flex items-center gap-2">
            <Radio className="w-4 h-4 text-cyan-400" />
            RECENT THREAT DETECTIONS
          </h2>
          <NavLink to="/detections" className="text-xs text-cyan-400 hover:underline font-mono">
            View All Detections →
          </NavLink>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Threat Name</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Risk Score</th>
                <th className="py-2.5 px-3">Detection Type</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Detected At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {recentThreats && recentThreats.items.length > 0 ? (
                recentThreats.items.map((threat) => (
                  <tr key={threat.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-3 font-semibold text-slate-200">{threat.threat_name}</td>
                    <td className="py-3 px-3">
                      <StatusBadge status={threat.severity} />
                    </td>
                    <td className="py-3 px-3">
                      <span className="font-bold text-red-400">{threat.risk_score}</span> / 100
                    </td>
                    <td className="py-3 px-3 text-slate-400">{threat.detection_type}</td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] ${threat.status === 'ACTIVE' ? 'bg-red-950 text-red-400 border border-red-800' : 'bg-slate-800 text-slate-300'}`}>
                        {threat.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-500">
                      {new Date(threat.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    <CheckCircle2 className="w-6 h-6 text-emerald-500/60 mx-auto mb-2" />
                    No active ransomware outbreaks detected. All endpoints secure.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

