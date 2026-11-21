import React, { useEffect, useState } from 'react';
import { CheckCircle2, Copy, Check, ArrowRight, ShieldCheck } from 'lucide-react';

export type SuccessRole = 'INDIVIDUAL' | 'ADMIN' | 'EMPLOYEE';

interface AuthSuccessModalProps {
  isOpen: boolean;
  role: SuccessRole;
  organizationName?: string | null;
  inviteCode?: string | null;
  onProceed: () => void;
}

export const AuthSuccessModal: React.FC<AuthSuccessModalProps> = ({
  isOpen,
  role,
  organizationName,
  inviteCode,
  onProceed,
}) => {
  const [copied, setCopied] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!isOpen) {
      setProgress(0);
      return;
    }

    // 1.8s progress bar and automatic redirect
    const intervalTime = 30; // update every 30ms
    const totalDuration = 1800; // 1.8 seconds
    const increment = (intervalTime / totalDuration) * 100;

    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(timer);
          onProceed();
          return 100;
        }
        return prev + increment;
      });
    }, intervalTime);

    return () => clearInterval(timer);
  }, [isOpen, onProceed]);

  if (!isOpen) return null;

  const handleCopyCode = () => {
    if (inviteCode) {
      navigator.clipboard.writeText(inviteCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="w-full max-w-md bg-[#090e17] border border-cyan-500/40 rounded-2xl p-6 shadow-2xl shadow-cyan-950/60 font-mono text-center space-y-5 animate-scaleUp">
        {/* Animated Checkmark Icon */}
        <div className="w-16 h-16 rounded-2xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-400 flex items-center justify-center mx-auto shadow-lg shadow-emerald-950/40 ring-4 ring-emerald-500/10 animate-pulse">
          <ShieldCheck className="w-9 h-9" />
        </div>

        {/* Content By Role */}
        {role === 'INDIVIDUAL' && (
          <div className="space-y-1.5">
            <h3 className="text-lg font-bold text-slate-100 flex items-center justify-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span>Account Created Successfully</span>
            </h3>
            <p className="text-xs text-slate-300">Welcome to VaultGuard.</p>
            <p className="text-[11px] text-slate-500">Your personal zero-trust backup vault is ready.</p>
          </div>
        )}

        {role === 'ADMIN' && (
          <div className="space-y-3">
            <div className="space-y-1">
              <h3 className="text-lg font-bold text-slate-100 flex items-center justify-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span>Organization Created Successfully</span>
              </h3>
              <p className="text-xs text-cyan-400 font-semibold">{organizationName}</p>
              <p className="text-[11px] text-slate-400">Administrator account created & verified.</p>
            </div>

            {inviteCode && (
              <div className="p-3.5 bg-slate-900/90 rounded-xl border border-cyan-500/30 text-left space-y-2">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                  Employee Invitation Code:
                </span>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-base font-bold text-cyan-300 tracking-widest bg-cyan-950/50 px-3 py-1 rounded border border-cyan-500/30">
                    {inviteCode}
                  </span>
                  <button
                    type="button"
                    onClick={handleCopyCode}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium transition-colors shadow-sm cursor-pointer"
                  >
                    {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <p className="text-[10px] text-slate-500">
                  Share this code with employees so they can join during registration.
                </p>
              </div>
            )}
          </div>
        )}

        {role === 'EMPLOYEE' && (
          <div className="space-y-2">
            <h3 className="text-lg font-bold text-slate-100 flex items-center justify-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span>Employee Account Created Successfully</span>
            </h3>
            <p className="text-xs text-slate-300">
              Welcome to <span className="text-cyan-400 font-bold">{organizationName || 'your organization'}</span>.
            </p>
            <p className="text-[11px] text-slate-500">
              Your workstation backup profile has been linked to the organization vault.
            </p>
          </div>
        )}

        {/* Dynamic Redirect Progress Bar */}
        <div className="space-y-1.5 pt-2">
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>
              Redirecting to{' '}
              {role === 'ADMIN'
                ? 'Admin Dashboard'
                : role === 'EMPLOYEE'
                ? 'Employee Dashboard'
                : 'Personal Dashboard'}
              ...
            </span>
            <span className="text-cyan-400">{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-cyan-500 h-full rounded-full transition-all duration-75"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Immediate Go To Dashboard Button */}
        <button
          type="button"
          onClick={onProceed}
          className="w-full py-2.5 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors shadow-md cursor-pointer"
        >
          <span>Go To Dashboard Now</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
