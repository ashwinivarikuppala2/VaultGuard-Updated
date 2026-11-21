import React from 'react';
import { Sliders, Shield, Lock, FileCheck2, Clock } from 'lucide-react';
import { BackupPolicy } from '../types';

export const BackupPolicies: React.FC = () => {
  const policies: BackupPolicy[] = [
    {
      id: 'pol-001',
      name: 'Real-Time Endpoint Protection',
      schedule_type: 'CONTINUOUS',
      retention_days: 30,
      compression_level: 6,
      encryption_standard: 'AES-256-GCM',
      is_active: true,
    },
    {
      id: 'pol-002',
      name: 'High-Integrity Server Snapshot',
      schedule_type: 'HOURLY',
      retention_days: 90,
      compression_level: 9,
      encryption_standard: 'AES-256-GCM',
      is_active: true,
    },
    {
      id: 'pol-003',
      name: 'Compliance Archive Standard',
      schedule_type: 'DAILY',
      retention_days: 365,
      compression_level: 9,
      encryption_standard: 'AES-256-GCM',
      is_active: false,
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl">
      <div className="pb-4 border-b border-slate-800">
        <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
          <Sliders className="w-5 h-5 text-cyan-400" />
          ENTERPRISE BACKUP POLICIES & ENCRYPTION RULES
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Automated frequency rules, cryptographic standards, retention schedules, and compression algorithms
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {policies.map((pol) => (
          <div
            key={pol.id}
            className={`cyber-card p-6 flex flex-col justify-between border ${
              pol.is_active ? 'border-cyan-500/40 bg-slate-900/40' : 'border-slate-800 bg-slate-900/20 opacity-75'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                  {pol.schedule_type}
                </span>
                <span
                  className={`text-[10px] font-mono font-semibold ${
                    pol.is_active ? 'text-emerald-400' : 'text-slate-500'
                  }`}
                >
                  {pol.is_active ? '• ACTIVE' : 'INACTIVE'}
                </span>
              </div>

              <h3 className="text-sm font-bold text-slate-100 font-mono mb-2">{pol.name}</h3>

              <div className="space-y-2.5 pt-3 border-t border-slate-800/80 text-xs font-mono text-slate-300">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-cyan-400" /> Cipher
                  </span>
                  <span className="text-cyan-300 font-bold">{pol.encryption_standard}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 flex items-center gap-1.5">
                    <FileCheck2 className="w-3.5 h-3.5 text-emerald-400" /> Compression
                  </span>
                  <span>zlib (Level {pol.compression_level})</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-amber-400" /> Retention
                  </span>
                  <span>{pol.retention_days} Days</span>
                </div>
              </div>
            </div>

            <div className="pt-4 mt-4 border-t border-slate-800/60">
              <button
                disabled={pol.is_active}
                className="w-full py-2 rounded-lg text-xs font-mono font-semibold transition-all border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-50"
              >
                {pol.is_active ? 'Policy Enforced' : 'Activate Policy'}
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="cyber-card p-6 border-cyan-500/20 bg-cyan-950/10">
        <h4 className="text-xs font-semibold text-cyan-300 font-mono uppercase tracking-wider mb-1 flex items-center gap-2">
          <Shield className="w-4 h-4" /> Cryptographic Policy Enforcement
        </h4>
        <p className="text-xs text-slate-300 leading-relaxed">
          All policies enforce AES-256-GCM authenticated encryption at the agent and server boundary. Plaintext files never enter MinIO object storage. Keys are generated with 256-bit entropy isolated per organization.
        </p>
      </div>
    </div>
  );
};

