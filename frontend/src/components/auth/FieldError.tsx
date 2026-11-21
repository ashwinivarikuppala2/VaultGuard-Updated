import React from 'react';
import { AlertCircle } from 'lucide-react';

interface FieldErrorProps {
  error?: string | null;
}

export const FieldError: React.FC<FieldErrorProps> = ({ error }) => {
  if (!error) return null;

  return (
    <div className="flex items-center gap-1.5 mt-1 text-xs text-red-400 font-mono animate-fadeIn">
      <AlertCircle className="w-3.5 h-3.5 shrink-0 text-red-400" />
      <span>{error}</span>
    </div>
  );
};
