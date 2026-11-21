import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export const AuthLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#06090e] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="min-h-screen bg-[#06090e] flex flex-col justify-center items-center p-4 relative overflow-hidden">
      {/* Background ambient cybersecurity glows */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md z-10">
        <div className="text-center mb-8">
          <div className="inline-flex p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 mb-3 shadow-lg shadow-cyan-950/30">
            <Shield className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100 font-mono">VAULTGUARD</h1>
          <p className="text-xs font-mono tracking-wider text-slate-400 uppercase mt-1">
            Secure Cloud Backup & Anti-Ransomware Platform
          </p>
        </div>

        <div className="cyber-card p-8 border border-slate-800 shadow-2xl bg-[#090e17]/95">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

