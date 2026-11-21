import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Building2,
  HardDrive,
  UserCheck,
  Sliders,
  ShieldCheck,
  FolderLock,
  History,
  PieChart,
  Activity,
  ShieldAlert,
  AlertTriangle,
  Radio,
  Lock,
  TrendingUp,
  RotateCcw,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const role = user?.role?.name || 'INDIVIDUAL';

  let navItems: { name: string; path: string; icon: any }[] = [];

  if (role === 'INDIVIDUAL') {
    navItems = [
      { name: 'Personal Dashboard', path: '/dashboard', icon: LayoutDashboard },
      { name: 'My Device', path: '/devices', icon: HardDrive },
      { name: 'Backup Center', path: '/backups', icon: ShieldCheck },
      { name: 'Backup History', path: '/backup-jobs', icon: Activity },
      { name: 'Protected Files', path: '/protected-folders', icon: FolderLock },
      { name: 'Ransomware Protection', path: '/dashboard/ransomware', icon: ShieldAlert },
      { name: 'Version History', path: '/version-history', icon: History },
      { name: 'Storage Usage', path: '/storage-analytics', icon: PieChart },
      { name: 'Threat Alerts', path: '/alerts', icon: AlertTriangle },
      { name: 'Recovery Center', path: '/recovery', icon: RotateCcw },
      { name: 'Profile', path: '/profile', icon: UserCheck },
      { name: 'Settings', path: '/settings', icon: Sliders },
    ];
  } else if (role === 'EMPLOYEE') {
    navItems = [
      { name: 'Employee Dashboard', path: '/employee/dashboard', icon: LayoutDashboard },
      { name: 'My Device', path: '/devices', icon: HardDrive },
      { name: 'Backup Center', path: '/backups', icon: ShieldCheck },
      { name: 'Protected Files', path: '/protected-folders', icon: FolderLock },
      { name: 'Ransomware Protection', path: '/employee/ransomware', icon: ShieldAlert },
      { name: 'Version History', path: '/version-history', icon: History },
      { name: 'Storage Used', path: '/storage-analytics', icon: PieChart },
      { name: 'Threat Alerts', path: '/alerts', icon: AlertTriangle },
      { name: 'Recovery', path: '/recovery', icon: RotateCcw },
      { name: 'My Organization', path: '/organizations', icon: Building2 },
      { name: 'Profile', path: '/profile', icon: UserCheck },
      { name: 'Settings', path: '/settings', icon: Sliders },
    ];
  } else {
    // ADMIN
    navItems = [
      { name: 'Admin Dashboard', path: '/admin/dashboard', icon: LayoutDashboard },
      { name: 'Organization & Invites', path: '/organizations', icon: Building2 },
      { name: 'Fleet Devices', path: '/devices', icon: HardDrive },
      { name: 'Backup Center', path: '/backups', icon: ShieldCheck },
      { name: 'Fleet Backup Jobs', path: '/backup-jobs', icon: Activity },
      { name: 'Protected Folders', path: '/protected-folders', icon: FolderLock },
      { name: 'Ransomware Protection', path: '/admin/ransomware', icon: ShieldAlert },
      { name: 'Version History', path: '/version-history', icon: History },
      { name: 'Storage Analytics', path: '/storage-analytics', icon: PieChart },
      { name: 'Backup Policies', path: '/backup-policies', icon: Sliders },
      { name: 'Threat Dashboard', path: '/threats', icon: ShieldAlert },
      { name: 'Detections', path: '/detections', icon: Radio },
      { name: 'Live Telemetry', path: '/live-events', icon: Activity },
      { name: 'Alert Center', path: '/alerts', icon: AlertTriangle },
      { name: 'Quarantine Center', path: '/quarantine', icon: Lock },
      { name: 'Threat Analytics', path: '/threat-analytics', icon: TrendingUp },
      { name: 'Risk Policies', path: '/risk-policies', icon: Sliders },
      { name: 'Recovery Center', path: '/recovery', icon: RotateCcw },
      { name: 'Profile', path: '/profile', icon: UserCheck },
      { name: 'Settings', path: '/settings', icon: Sliders },
    ];
  }

  return (
    <aside className="w-64 bg-[#06090e] border-r border-slate-800/80 flex flex-col justify-between shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-6">
        <div>
          <p className="px-3 text-[10px] font-mono tracking-wider text-slate-300 uppercase mb-2">
            Platform Navigation
          </p>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-lg shadow-cyan-950/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        <div className="pt-4 border-t border-slate-800/60">
          <p className="px-3 text-[10px] font-mono tracking-wider text-slate-300 uppercase mb-2">
            Module Readiness
          </p>
          <div className="space-y-2 px-3">
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                M1: Foundation
              </span>
              <span className="text-[10px] font-mono text-emerald-400">ACTIVE</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                M2: Backup Engine
              </span>
              <span className="text-[10px] font-mono text-emerald-400">ACTIVE</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                M3: Threat Defense
              </span>
              <span className="text-[10px] font-mono text-emerald-400">ACTIVE</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                M4: Recovery Engine
              </span>
              <span className="text-[10px] font-mono text-emerald-400">ACTIVE</span>
            </div>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-slate-800/80 bg-[#090e17]/50">
        <div className="flex items-center space-x-2 text-xs text-slate-400">
          <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
          <span className="font-mono">VaultGuard Node #1 Online</span>
        </div>
      </div>
    </aside>
  );
};

