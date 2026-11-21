import React from 'react';
import { Shield, Bell, User as UserIcon, LogOut } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 bg-[#090e17]/90 backdrop-blur-md border-b border-slate-800/80 px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center space-x-3">
        <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <span className="font-mono text-sm tracking-widest text-slate-400">SECURE CLOUD BACKUP</span>
          <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
            VAULTGUARD <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-mono">v1.0</span>
          </h2>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <button
          className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/50 transition-colors relative"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-cyan-500" />
        </button>

        <div className="h-5 w-px bg-slate-800" />

        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-cyan-400 font-mono text-xs">
            {user?.full_name ? user.full_name[0].toUpperCase() : <UserIcon className="w-4 h-4" />}
          </div>
          <div className="text-left hidden md:block">
            <p className="text-xs font-medium text-slate-200">{user?.full_name}</p>
            <p className="text-[10px] font-mono text-cyan-400">{user?.role?.name}</p>
          </div>
          <button
            onClick={logout}
            className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors ml-2"
            title="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};

