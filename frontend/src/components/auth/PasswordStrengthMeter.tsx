import React from 'react';
import { PasswordStrength } from '../../utils/authValidation';

interface PasswordStrengthMeterProps {
  strength: PasswordStrength;
  visible: boolean;
}

export const PasswordStrengthMeter: React.FC<PasswordStrengthMeterProps> = ({ strength, visible }) => {
  if (!visible) return null;

  return (
    <div className="mt-2 space-y-1.5 font-mono text-xs">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-slate-400">Password Strength:</span>
        <span
          className={`font-semibold ${
            strength.score <= 1
              ? 'text-red-400'
              : strength.score === 2
              ? 'text-amber-400'
              : strength.score === 3
              ? 'text-cyan-400'
              : 'text-emerald-400'
          }`}
        >
          {strength.label}
        </span>
      </div>

      {/* 4-bar strength indicator */}
      <div className="grid grid-cols-4 gap-1.5 h-1.5">
        {[1, 2, 3, 4].map((step) => (
          <div
            key={step}
            className={`rounded-full transition-all duration-300 ${
              strength.score >= step ? strength.color : 'bg-slate-800'
            }`}
          />
        ))}
      </div>

      {/* Requirements checklist */}
      <div className="grid grid-cols-2 gap-x-2 gap-y-1 pt-1 text-[10px] text-slate-400">
        <span className={strength.hasLength ? 'text-emerald-400' : 'text-slate-500'}>
          {strength.hasLength ? '✓' : '•'} At least 8 characters
        </span>
        <span className={strength.hasUpper && strength.hasLower ? 'text-emerald-400' : 'text-slate-500'}>
          {strength.hasUpper && strength.hasLower ? '✓' : '•'} Upper & lowercase
        </span>
        <span className={strength.hasNumber ? 'text-emerald-400' : 'text-slate-500'}>
          {strength.hasNumber ? '✓' : '•'} At least 1 number
        </span>
        <span className={strength.hasSpecial ? 'text-emerald-400' : 'text-slate-500'}>
          {strength.hasSpecial ? '✓' : '•'} At least 1 symbol
        </span>
      </div>
    </div>
  );
};
