import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Building2,
  Mail,
  AlertCircle,
  KeyRound,
  Copy,
  Check,
  RefreshCw,
  Users,
  HardDrive,
  Cpu,
  ShieldCheck,
  UserCheck,
  Sparkles,
} from 'lucide-react';
import { organizationService } from '../services/organizationService';
import { StatusBadge } from '../components/common/StatusBadge';
import { useAuth } from '../hooks/useAuth';
import { Modal } from '../components/common/Modal';
import { useToast } from '../contexts/ToastContext';

export const Organizations: React.FC = () => {
  const { user } = useAuth();
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const getRoleName = (u: any): string => {
    if (!u) return '';
    if (typeof u.role === 'string') return u.role;
    if (u.role?.name) return u.role.name;
    if (u.role_name) return u.role_name;
    return '';
  };

  const roleName = getRoleName(user);
  const isAdmin = roleName === 'ADMIN';
  const isIndividual = roleName === 'INDIVIDUAL';

  const [copiedCode, setCopiedCode] = useState(false);
  const [isConfirmRegenOpen, setIsConfirmRegenOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Query: Org info
  const { data: orgsData } = useQuery({
    queryKey: ['my-organization'],
    queryFn: () => organizationService.list(0, 1),
    enabled: !isIndividual,
  });

  // Query: Invite Code (Admin only)
  const { data: inviteData, isLoading: inviteLoading } = useQuery({
    queryKey: ['organization-invite-code'],
    queryFn: () => organizationService.getInviteCode(),
    enabled: isAdmin,
    staleTime: 1000 * 30, // 30 seconds
  });

  // Query: Employees list (Admin only)
  const { data: employeesData, isLoading: employeesLoading } = useQuery({
    queryKey: ['organization-employees'],
    queryFn: () => organizationService.listEmployees(),
    enabled: isAdmin,
  });

  // Mutation: Regenerate or Generate invite code
  const regenMutation = useMutation({
    mutationFn: organizationService.regenerateInviteCode,
    onSuccess: (data) => {
      queryClient.setQueryData(['organization-invite-code'], data);
      queryClient.invalidateQueries({ queryKey: ['admin-invite-code'] });
      setIsConfirmRegenOpen(false);
      showToast('✓ Invite Code Generated Successfully');
    },
    onError: (err: any) => {
      const msg = err.response?.data?.error?.message || err.response?.data?.detail || 'Failed to update invite code.';
      setError(msg);
      showToast(msg, 'error');
    },
  });

  const currentOrg = orgsData?.items?.[0];
  const currentInviteCode = inviteData?.invite_code || currentOrg?.invite_code || '';
  const hasInviteCode = Boolean(currentInviteCode && currentInviteCode.trim() !== '' && currentInviteCode !== 'NONE');

  const handleCopyInviteCode = () => {
    if (currentInviteCode) {
      navigator.clipboard.writeText(currentInviteCode);
      setCopiedCode(true);
      showToast('✓ Invite Code Copied to Clipboard');
      setTimeout(() => setCopiedCode(false), 2500);
    }
  };

  const handleRegenerateClick = () => {
    setError(null);
    setIsConfirmRegenOpen(true);
  };

  const handleConfirmRegenerate = () => {
    setError(null);
    regenMutation.mutate();
  };

  const handleGenerateCode = () => {
    setError(null);
    regenMutation.mutate();
  };

  if (isIndividual) {
    return (
      <div className="space-y-6">
        <div className="pb-4 border-b border-slate-800">
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <Building2 className="w-5 h-5 text-cyan-400" />
            <span>ORGANIZATION STATUS</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Personal Account Workspace • Standalone Mode
          </p>
        </div>

        <div className="cyber-card p-6 border-slate-800 bg-slate-900/40 text-center max-w-xl mx-auto space-y-4">
          <div className="w-12 h-12 rounded-xl bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 flex items-center justify-center mx-auto">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-200">Personal Account Active</h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              You are currently utilizing VaultGuard in Personal Use mode. Your backup keys, recovery snapshots, and protected folders are isolated strictly to your user profile without an organization.
            </p>
          </div>
          <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800 text-left text-xs space-y-1 text-slate-300">
            <p><strong className="text-slate-100">User:</strong> {user?.full_name} ({user?.email})</p>
            <p><strong className="text-slate-100">Role:</strong> INDIVIDUAL</p>
            <p><strong className="text-slate-100">Organization:</strong> None (Standalone)</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <Building2 className="w-5 h-5 text-cyan-400" />
            <span>ORGANIZATION & INVITES</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {isAdmin
              ? 'Manage organization credentials, employee invitation codes, and enrolled workforce'
              : 'Enrolled organization details and team membership'}
          </p>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Org Overview Cards */}
      {currentOrg && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="cyber-card p-4 space-y-1">
            <p className="text-[11px] font-mono text-slate-400 uppercase">Organization Name</p>
            <p className="text-base font-semibold text-slate-100">{currentOrg.name}</p>
            <p className="text-xs text-slate-500 font-mono">{currentOrg.slug}</p>
          </div>

          <div className="cyber-card p-4 space-y-1">
            <p className="text-[11px] font-mono text-slate-400 uppercase">Contact & Status</p>
            <div className="flex items-center gap-1.5 text-xs text-slate-300">
              <Mail className="w-3.5 h-3.5 text-slate-500" />
              <span>{currentOrg.contact_email}</span>
            </div>
            <div className="pt-1">
              <StatusBadge status={currentOrg.is_active ? 'HEALTHY' : 'UNHEALTHY'} />
            </div>
          </div>

          <div className="cyber-card p-4 space-y-1">
            <p className="text-[11px] font-mono text-slate-400 uppercase">Fleet Quotas</p>
            <div className="flex items-center gap-4 text-xs font-mono">
              <span className="flex items-center gap-1 text-slate-300">
                <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                <span>Max: <strong>{currentOrg.max_devices}</strong> devices</span>
              </span>
              <span className="flex items-center gap-1 text-slate-300">
                <HardDrive className="w-3.5 h-3.5 text-cyan-400" />
                <span>{(currentOrg.storage_quota_bytes / (1024 * 1024 * 1024)).toFixed(0)} GB</span>
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Admin Section: Invite Code Management */}
      {isAdmin && (
        <div className="cyber-card p-5 border-cyan-500/30 bg-cyan-950/10 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-cyan-400" />
                <span>Employee Invitation Code</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Share this secure code with employees so they can join this organization during registration.
              </p>
            </div>

            {/* Buttons: Always visible */}
            <div className="flex items-center gap-2 flex-wrap">
              {hasInviteCode ? (
                <>
                  <button
                    type="button"
                    onClick={handleCopyInviteCode}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium transition-colors shadow-sm cursor-pointer"
                  >
                    {copiedCode ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedCode ? 'Copied!' : 'Copy Code'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleRegenerateClick}
                    disabled={regenMutation.isPending}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium transition-colors border border-slate-700 cursor-pointer disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${regenMutation.isPending ? 'animate-spin' : ''}`} />
                    <span>Regenerate</span>
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={handleGenerateCode}
                  disabled={regenMutation.isPending}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{regenMutation.isPending ? 'Generating...' : 'Generate Invite Code'}</span>
                </button>
              )}
            </div>
          </div>

          {/* Invitation Code Display Box */}
          <div className="p-4 bg-slate-900/90 rounded-lg border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Active Invitation Code:
            </span>

            {inviteLoading ? (
              <span className="text-xs font-mono text-cyan-400/80 animate-pulse">
                Loading invitation code...
              </span>
            ) : hasInviteCode ? (
              <div className="flex items-center gap-3">
                <span className="text-base sm:text-lg font-mono font-bold tracking-widest text-cyan-300 bg-cyan-950/60 px-4 py-1.5 rounded-lg border border-cyan-500/40 shadow-inner">
                  {currentInviteCode}
                </span>
                <button
                  type="button"
                  onClick={handleCopyInviteCode}
                  title="Copy Invite Code"
                  className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700"
                >
                  {copiedCode ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-xs font-mono text-amber-400/90 italic">
                  No invitation code has been generated.
                </span>
                <button
                  type="button"
                  onClick={handleGenerateCode}
                  disabled={regenMutation.isPending}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-mono transition-colors shadow-sm disabled:opacity-50 cursor-pointer"
                >
                  <Sparkles className="w-3 h-3" />
                  <span>Generate Invite Code</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Admin Section: Enrolled Employees Table */}
      {isAdmin && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2">
              <Users className="w-4 h-4 text-cyan-400" />
              <span>ENROLLED ORGANIZATION MEMBERS</span>
            </h2>
            <span className="text-xs font-mono text-slate-400">
              {employeesData?.length || 0} Members
            </span>
          </div>

          <div className="cyber-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 font-mono">
                    <th className="py-3 px-4 font-medium">Name</th>
                    <th className="py-3 px-4 font-medium">Work Email</th>
                    <th className="py-3 px-4 font-medium">Role</th>
                    <th className="py-3 px-4 font-medium">Account Status</th>
                    <th className="py-3 px-4 font-medium">Enrolled Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {employeesLoading ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-500">
                        Loading organization members...
                      </td>
                    </tr>
                  ) : (employeesData ?? []).length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-500">
                        No employees enrolled yet. Share your invite code above to onboard team members.
                      </td>
                    </tr>
                  ) : (
                    employeesData?.map((emp) => (
                      <tr key={emp.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3.5 px-4 font-semibold text-slate-200 flex items-center gap-2">
                          <UserCheck className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                          <span>{emp.full_name}</span>
                        </td>
                        <td className="py-3.5 px-4 text-slate-300">{emp.email}</td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              emp.role?.name === 'ADMIN'
                                ? 'bg-purple-950/60 text-purple-400 border border-purple-500/30'
                                : 'bg-cyan-950/60 text-cyan-400 border border-cyan-500/30'
                            }`}
                          >
                            {emp.role?.name}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <StatusBadge status={emp.is_active ? 'HEALTHY' : 'UNHEALTHY'} />
                        </td>
                        <td className="py-3.5 px-4 text-slate-500">
                          {new Date(emp.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Invite Code Regeneration */}
      <Modal
        isOpen={isConfirmRegenOpen}
        onClose={() => setIsConfirmRegenOpen(false)}
        title="Regenerate Organization Invite Code"
      >
        <div className="space-y-4 font-mono text-xs">
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-300 space-y-1">
            <p className="font-semibold text-amber-200">Warning: Invalidation of Current Code</p>
            <p className="text-[11px] leading-relaxed">
              Are you sure you want to regenerate the invite code? The current code{' '}
              <strong className="text-cyan-400">{currentInviteCode || 'active code'}</strong> will immediately become invalid.
              Any employee attempting to register with the old code will be rejected.
            </p>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setIsConfirmRegenOpen(false)}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirmRegenerate}
              disabled={regenMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${regenMutation.isPending ? 'animate-spin' : ''}`} />
              <span>{regenMutation.isPending ? 'Regenerating...' : 'Yes, Regenerate Code'}</span>
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
