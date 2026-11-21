import React from 'react';
import { Sliders, Lock, Server } from 'lucide-react';

export const Settings: React.FC = () => {
  return (
    <div className="space-y-6 max-w-4xl">
      <div className="pb-4 border-b border-slate-800">
        <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
          <Sliders className="w-5 h-5 text-cyan-400" />
          SYSTEM CONFIGURATION & SECURITY CONTROLS
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Immutable platform security parameters and runtime defense flags (Module 1)
        </p>
      </div>

      <div className="space-y-4">
        {/* Security Parameters */}
        <div className="cyber-card p-6">
          <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2 mb-4 font-mono">
            <Lock className="w-4 h-4 text-cyan-400" />
            Zero-Trust Authentication & Token Lifecycles
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-xs">
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block">Access Token Lifespan</span>
              <span className="text-slate-200 font-semibold mt-1 block">30 Minutes (HS256 Signed)</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block">Refresh Token Rotation</span>
              <span className="text-slate-200 font-semibold mt-1 block">7 Days (Hashed In PostgreSQL)</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block">Password Hashing Algorithm</span>
              <span className="text-slate-200 font-semibold mt-1 block">BCrypt (Cost Factor 12)</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block">Access Control Policy</span>
              <span className="text-emerald-400 font-semibold mt-1 block">Enforced RBAC (Super / Org / Emp)</span>
            </div>
          </div>
        </div>

        {/* Storage & Queue Parameters */}
        <div className="cyber-card p-6">
          <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2 mb-4 font-mono">
            <Server className="w-4 h-4 text-emerald-400" />
            Infrastructure Topology
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-xs">
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block">MinIO S3 Immutable Bucket</span>
              <span className="text-slate-200 font-semibold mt-1 block">vaultguard-storage</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block">Celery Broker / Backend</span>
              <span className="text-slate-200 font-semibold mt-1 block">Redis 7 (db 1 / db 2)</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block">Primary Relational Store</span>
              <span className="text-slate-200 font-semibold mt-1 block">PostgreSQL 16 (Async SQLAlchemy)</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block">Database Migrations</span>
              <span className="text-slate-200 font-semibold mt-1 block">Alembic Automated Versioning</span>
            </div>
          </div>
        </div>

        {/* Future Modules Integration Roadmap Notice */}
        <div className="cyber-card p-6 border-cyan-500/30 bg-cyan-950/10">
          <h4 className="text-xs font-semibold text-cyan-300 font-mono uppercase tracking-wider mb-2">
            Module 1 Architecture Constraint
          </h4>
          <p className="text-xs text-slate-300 leading-relaxed">
            All foundation schemas, connection pools, and API models are locked to prevent redesigns.
            Future Modules 2 (Ransomware Heuristics), 3 (Quarantine & Recovery), and 4 (Backup Scheduling)
            will extend these endpoints and tables seamlessly.
          </p>
        </div>
      </div>
    </div>
  );
};

