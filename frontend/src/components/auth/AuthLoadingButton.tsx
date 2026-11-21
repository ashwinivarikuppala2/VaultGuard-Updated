import React from 'react';
import { Loader2 } from 'lucide-react';

interface AuthLoadingButtonProps {
  isLoading: boolean;
  loadingText: string;
  defaultText: string;
  icon?: React.ReactNode;
  disabled?: boolean;
  type?: 'submit' | 'button';
  onClick?: () => void;
  className?: string;
}

export const AuthLoadingButton: React.FC<AuthLoadingButtonProps> = ({
  isLoading,
  loadingText,
  defaultText,
  icon,
  disabled = false,
  type = 'submit',
  onClick,
  className = '',
}) => {
  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={`w-full py-3 px-4 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-cyan-950/40 flex items-center justify-center gap-2 group cursor-pointer ${className}`}
    >
      {isLoading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-white/90" />
          <span className="font-mono">{loadingText}</span>
        </>
      ) : (
        <>
          <span className="font-mono">{defaultText}</span>
          {icon && <span className="group-hover:translate-x-0.5 transition-transform">{icon}</span>}
        </>
      )}
    </button>
  );
};
