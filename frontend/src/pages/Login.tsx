import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Lock, Mail, AlertCircle, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useAuth, getDashboardRouteForRole } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { validateEmail, parseApiError } from '../utils/authValidation';
import { FieldError } from '../components/auth/FieldError';
import { AuthLoadingButton } from '../components/auth/AuthLoadingButton';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Field validation errors
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [loginSuccess, setLoginSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const handleEmailChange = (val: string) => {
    setEmail(val);
    if (fieldErrors.email) {
      setFieldErrors((prev) => ({ ...prev, email: undefined }));
    }
    if (formError) setFormError(null);
  };

  const handlePasswordChange = (val: string) => {
    setPassword(val);
    if (fieldErrors.password) {
      setFieldErrors((prev) => ({ ...prev, password: undefined }));
    }
    if (formError) setFormError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting || loginSuccess) return;

    // Client-side validations
    const errors: { email?: string; password?: string } = {};
    const emailErr = validateEmail(email);
    if (emailErr) errors.email = emailErr;

    if (!password.trim()) {
      errors.password = 'Password is required.';
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setFieldErrors({});
    setFormError(null);
    setIsSubmitting(true);

    try {
      const user = await login(email.trim(), password);
      setLoginSuccess(true);
      showToast('✓ Login Successful');

      const targetRoute = getDashboardRouteForRole(user?.role);
      setTimeout(() => {
        navigate(targetRoute);
      }, 700);
    } catch (err: any) {
      const parsed = parseApiError(err);
      setFormError(parsed.message);
      if (parsed.fieldErrors.email) {
        setFieldErrors((prev) => ({ ...prev, email: parsed.fieldErrors.email }));
      }
      showToast(parsed.message, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-slate-100 font-mono">Sign In to VaultGuard</h2>
        <p className="text-xs text-slate-400 mt-1">Authenticate to access your defense vault and recovery pane</p>
      </div>

      {formError && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2 font-mono animate-fadeIn">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{formError}</span>
        </div>
      )}

      {loginSuccess && (
        <div className="mb-4 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2 font-mono animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>✓ Login Successful. Redirecting...</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* Email Field */}
        <div>
          <label className="block text-xs font-mono text-slate-300 mb-1.5 uppercase">
            Email Address
          </label>
          <div className="relative">
            <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" />
            <input
              type="email"
              value={email}
              onChange={(e) => handleEmailChange(e.target.value)}
              placeholder="operator@vaultguard.internal"
              disabled={isSubmitting || loginSuccess}
              className={`w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border rounded-lg text-sm text-slate-100 focus:outline-none transition-colors placeholder:text-slate-600 font-mono ${
                fieldErrors.email
                  ? 'border-red-500/80 focus:border-red-500'
                  : 'border-slate-700/80 focus:border-cyan-500'
              }`}
            />
          </div>
          <FieldError error={fieldErrors.email} />
        </div>

        {/* Password Field */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-xs font-mono text-slate-300 uppercase">Password</label>
          </div>
          <div className="relative">
            <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" />
            <input
              type="password"
              value={password}
              onChange={(e) => handlePasswordChange(e.target.value)}
              placeholder="••••••••••••"
              disabled={isSubmitting || loginSuccess}
              className={`w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border rounded-lg text-sm text-slate-100 focus:outline-none transition-colors placeholder:text-slate-600 font-mono ${
                fieldErrors.password
                  ? 'border-red-500/80 focus:border-red-500'
                  : 'border-slate-700/80 focus:border-cyan-500'
              }`}
            />
          </div>
          <FieldError error={fieldErrors.password} />
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <AuthLoadingButton
            isLoading={isSubmitting || loginSuccess}
            loadingText={loginSuccess ? 'Redirecting...' : 'Signing In...'}
            defaultText="Authenticate Session"
            icon={<ArrowRight className="w-4 h-4" />}
          />
        </div>
      </form>

      <div className="mt-6 pt-6 border-t border-slate-800 text-center">
        <p className="text-xs text-slate-400">
          Need an account?{' '}
          <Link to="/register" className="text-cyan-400 hover:underline font-medium">
            Create an Account
          </Link>
        </p>
      </div>
    </div>
  );
};
