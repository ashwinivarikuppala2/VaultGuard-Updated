import React from 'react';
import { User, Shield } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export const Profile: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="pb-4 border-b border-slate-800">
        <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
          <User className="w-5 h-5 text-cyan-400" />
          AUTHENTICATED OPERATOR PROFILE
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Cryptographic credentials, role access grants, and security attributes
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="cyber-card p-6 flex flex-col items-center text-center">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center text-2xl font-bold font-mono text-white shadow-xl shadow-cyan-950/50 mb-4">
            {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
          </div>
          <h2 className="text-base font-semibold text-slate-100">{user?.full_name}</h2>
          <p className="text-xs font-mono text-slate-400 mt-0.5">{user?.email}</p>

          <div className="mt-4 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-mono text-xs">
            <Shield className="w-3.5 h-3.5" />
            <span>{user?.role?.name}</span>
          </div>
        </div>

        <div className="cyber-card p-6 md:col-span-2 space-y-4">
          <h3 className="text-sm font-semibold text-slate-200 font-mono uppercase tracking-wider pb-2 border-b border-slate-800">
            Account Specifications
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-xs">
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block mb-1">User Identifier</span>
              <span className="text-slate-200 truncate block">{user?.id}</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block mb-1">Assigned Tenant Org</span>
              <span className="text-slate-200 truncate block">
                {user?.organization_id || 'System Super Administrator'}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block mb-1">Account Status</span>
              <span className="text-emerald-400 font-bold">
                {user?.is_active ? 'ACTIVE & VERIFIED' : 'DISABLED'}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block mb-1">Last Authentication</span>
              <span className="text-slate-300">
                {user?.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Current Session'}
              </span>
            </div>
          </div>

          <div className="pt-2">
            <p className="text-xs text-slate-400 leading-relaxed">
              Sessions are cryptographically protected via rotated refresh tokens and short-lived JWTs.
              Privilege modifications require manual elevation from a platform Super Administrator.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

