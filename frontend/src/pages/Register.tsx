import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Lock,
  Mail,
  Building2,
  User,
  AlertCircle,
  ArrowRight,
  Shield,
  Laptop,
  KeyRound,
  CheckCircle2,
  HardDrive,
  Cpu,
  Loader2,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { authService } from '../services/authService';
import {
  validateEmail,
  validatePassword,
  validateFullName,
  validateOrgName,
  validateInviteCodeFormat,
  parseApiError,
  PasswordStrength,
} from '../utils/authValidation';
import { FieldError } from '../components/auth/FieldError';
import { PasswordStrengthMeter } from '../components/auth/PasswordStrengthMeter';
import { AuthLoadingButton } from '../components/auth/AuthLoadingButton';
import { AuthSuccessModal, SuccessRole } from '../components/auth/AuthSuccessModal';

type UsageMode = 'PERSONAL' | 'ORGANIZATION';
type OrgSubMode = 'CREATE' | 'JOIN';

export const Register: React.FC = () => {
  const [usageMode, setUsageMode] = useState<UsageMode>('PERSONAL');
  const [orgSubMode, setOrgSubMode] = useState<OrgSubMode>('CREATE');

  // Common Fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');

  // Org Admin Fields
  const [orgName, setOrgName] = useState('');
  const [storageQuotaGb, setStorageQuotaGb] = useState<number>(100);
  const [maxDevices, setMaxDevices] = useState<number>(50);

  // Employee Join Fields
  const [inviteCode, setInviteCode] = useState('');
  const [isValidatingCode, setIsValidatingCode] = useState(false);
  const [codeValidation, setCodeValidation] = useState<{
    isValid: boolean;
    orgName?: string | null;
    message?: string | null;
  } | null>(null);

  // Validation States
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Password Strength State
  const [passwordStrength, setPasswordStrength] = useState<PasswordStrength>({
    score: 0,
    label: 'Too Weak',
    color: 'bg-red-500',
    hasLength: false,
    hasUpper: false,
    hasLower: false,
    hasNumber: false,
    hasSpecial: false,
  });
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);

  // Success Modal State
  const [successModal, setSuccessModal] = useState<{
    isOpen: boolean;
    role: SuccessRole;
    orgName?: string | null;
    inviteCode?: string | null;
    redirectUrl: string;
  }>({
    isOpen: false,
    role: 'INDIVIDUAL',
    redirectUrl: '/dashboard',
  });

  const { registerPersonal, registerOrganization, registerEmployee } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  // Clear errors when typing
  const handleFieldChange = (field: string, setter: (val: string) => void, val: string) => {
    setter(val);
    if (fieldErrors[field]) {
      setFieldErrors((prev) => {
        const copy = { ...prev };
        delete copy[field];
        return copy;
      });
    }
    if (formError) setFormError(null);
  };

  const handlePasswordChange = (val: string) => {
    setPassword(val);
    const { strength, error } = validatePassword(val);
    setPasswordStrength(strength);
    if (fieldErrors.password && !error) {
      setFieldErrors((prev) => {
        const copy = { ...prev };
        delete copy.password;
        return copy;
      });
    }
    if (formError) setFormError(null);
  };

  // Validate invite code handler
  const handleValidateInviteCode = async () => {
    const cleanCode = inviteCode.trim().toUpperCase();
    const formatErr = validateInviteCodeFormat(cleanCode);
    if (formatErr) {
      setFieldErrors((prev) => ({ ...prev, invite_code: formatErr }));
      return;
    }

    setFieldErrors((prev) => {
      const copy = { ...prev };
      delete copy.invite_code;
      return copy;
    });
    setFormError(null);
    setIsValidatingCode(true);

    try {
      const res = await authService.validateInviteCode(cleanCode);
      if (res.is_valid) {
        setCodeValidation({
          isValid: true,
          orgName: res.organization_name,
          message: null,
        });
        showToast(`✓ Organization Found: ${res.organization_name}`);
      } else {
        const errMsg = res.message || 'Invalid Invitation Code';
        setCodeValidation({
          isValid: false,
          orgName: null,
          message: errMsg,
        });
        setFieldErrors((prev) => ({ ...prev, invite_code: errMsg }));
        showToast(errMsg, 'error');
      }
    } catch (err: any) {
      const parsed = parseApiError(err);
      const errMsg = parsed.fieldErrors.invite_code || parsed.message || 'Invalid Invitation Code';
      setCodeValidation({
        isValid: false,
        orgName: null,
        message: errMsg,
      });
      setFieldErrors((prev) => ({ ...prev, invite_code: errMsg }));
      showToast(errMsg, 'error');
    } finally {
      setIsValidatingCode(false);
    }
  };

  // Mode switcher with clean state
  const handleSelectMode = (mode: UsageMode) => {
    setUsageMode(mode);
    setFieldErrors({});
    setFormError(null);
  };

  const handleSelectOrgSubMode = (subMode: OrgSubMode) => {
    setOrgSubMode(subMode);
    setFieldErrors({});
    setFormError(null);
  };

  // Form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting || successModal.isOpen) return;

    // Validate fields
    const errors: Record<string, string> = {};

    const nameErr = validateFullName(fullName);
    if (nameErr) errors.full_name = nameErr;

    const emailErr = validateEmail(email);
    if (emailErr) errors.email = emailErr;

    const passResult = validatePassword(password);
    if (passResult.error) errors.password = passResult.error;

    if (usageMode === 'ORGANIZATION') {
      if (orgSubMode === 'CREATE') {
        const orgErr = validateOrgName(orgName);
        if (orgErr) errors.organization_name = orgErr;
      } else {
        // JOIN
        if (!codeValidation?.isValid) {
          errors.invite_code = 'Please enter and validate an invitation code before registering.';
        }
      }
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setFieldErrors({});
    setFormError(null);
    setIsSubmitting(true);

    try {
      if (usageMode === 'PERSONAL') {
        await registerPersonal({
          email: email.trim(),
          password,
          full_name: fullName.trim(),
        });
        showToast('✓ Registration Successful');
        setSuccessModal({
          isOpen: true,
          role: 'INDIVIDUAL',
          redirectUrl: '/dashboard',
        });
      } else if (orgSubMode === 'CREATE') {
        const quotaBytes = storageQuotaGb * 1024 * 1024 * 1024;
        const tokens = await registerOrganization({
          organization_name: orgName.trim(),
          email: email.trim(),
          password,
          full_name: fullName.trim(),
          storage_quota_bytes: quotaBytes,
          max_devices: maxDevices,
        });
        showToast('✓ Organization Created');
        setSuccessModal({
          isOpen: true,
          role: 'ADMIN',
          orgName: orgName.trim(),
          inviteCode: tokens.invite_code || 'VG-ACTIVE',
          redirectUrl: '/admin/dashboard',
        });
      } else {
        // JOIN as Employee
        const tokens = await registerEmployee({
          invite_code: inviteCode.trim().toUpperCase(),
          email: email.trim(),
          password,
          full_name: fullName.trim(),
        });
        showToast('✓ Registration Successful');
        setSuccessModal({
          isOpen: true,
          role: 'EMPLOYEE',
          orgName: codeValidation?.orgName || tokens.organization_name,
          redirectUrl: '/employee/dashboard',
        });
      }
    } catch (err: any) {
      const parsed = parseApiError(err);
      setFormError(parsed.message);
      if (Object.keys(parsed.fieldErrors).length > 0) {
        setFieldErrors((prev) => ({ ...prev, ...parsed.fieldErrors }));
      }
      showToast(parsed.message, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleModalProceed = () => {
    navigate(successModal.redirectUrl);
  };

  return (
    <div className="w-full">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <Shield className="w-5 h-5 text-cyan-400" />
          <span>Get Started with VaultGuard</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Zero-trust backup versioning and automated ransomware recovery
        </p>
      </div>

      {/* Mode Selector */}
      <div className="mb-6">
        <label className="block text-xs font-mono text-slate-300 mb-2 uppercase tracking-wider">
          How do you want to use VaultGuard?
        </label>
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => handleSelectMode('PERSONAL')}
            disabled={isSubmitting}
            className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
              usageMode === 'PERSONAL'
                ? 'border-cyan-500 bg-cyan-950/30 text-white ring-1 ring-cyan-500/50 shadow-md shadow-cyan-950/50'
                : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
            }`}
          >
            <div className="flex items-center gap-2.5 mb-1.5">
              <Laptop className={`w-4 h-4 ${usageMode === 'PERSONAL' ? 'text-cyan-400' : 'text-slate-500'}`} />
              <span className="text-xs font-bold font-mono">Personal Use</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Protect your personal laptop or desktop without an organization.
            </p>
          </button>

          <button
            type="button"
            onClick={() => handleSelectMode('ORGANIZATION')}
            disabled={isSubmitting}
            className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
              usageMode === 'ORGANIZATION'
                ? 'border-cyan-500 bg-cyan-950/30 text-white ring-1 ring-cyan-500/50 shadow-md shadow-cyan-950/50'
                : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
            }`}
          >
            <div className="flex items-center gap-2.5 mb-1.5">
              <Building2 className={`w-4 h-4 ${usageMode === 'ORGANIZATION' ? 'text-cyan-400' : 'text-slate-500'}`} />
              <span className="text-xs font-bold font-mono">Organization Use</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Create an organization or join an existing company team with an invite code.
            </p>
          </button>
        </div>
      </div>

      {/* Organization Submode Selector (Create vs Join) */}
      {usageMode === 'ORGANIZATION' && (
        <div className="mb-6 p-1.5 bg-slate-900/90 border border-slate-800 rounded-xl grid grid-cols-2 gap-1.5">
          <button
            type="button"
            onClick={() => handleSelectOrgSubMode('CREATE')}
            disabled={isSubmitting}
            className={`py-2 px-3 rounded-lg text-xs font-mono font-semibold transition-all cursor-pointer ${
              orgSubMode === 'CREATE'
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            1. Create Organization (Admin)
          </button>
          <button
            type="button"
            onClick={() => handleSelectOrgSubMode('JOIN')}
            disabled={isSubmitting}
            className={`py-2 px-3 rounded-lg text-xs font-mono font-semibold transition-all cursor-pointer ${
              orgSubMode === 'JOIN'
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            2. Join Organization (Employee)
          </button>
        </div>
      )}

      {/* Form Error Banner */}
      {formError && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2 font-mono animate-fadeIn">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{formError}</span>
        </div>
      )}

      {/* Main Form */}
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* EMPLOYEE FLOW: Step 1 Invite Code Validation */}
        {usageMode === 'ORGANIZATION' && orgSubMode === 'JOIN' && (
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-3">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5 uppercase">
                Invitation Code <span className="text-cyan-400">*</span>
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <KeyRound className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="text"
                    value={inviteCode}
                    onChange={(e) => {
                      const val = e.target.value.toUpperCase();
                      handleFieldChange('invite_code', setInviteCode, val);
                      setCodeValidation(null);
                    }}
                    placeholder="VG-8KQ2-LM4P"
                    disabled={isSubmitting || isValidatingCode}
                    className={`w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border rounded-lg text-sm text-cyan-300 tracking-wider focus:outline-none transition-colors placeholder:text-slate-600 font-mono ${
                      fieldErrors.invite_code
                        ? 'border-red-500 focus:border-red-500'
                        : 'border-slate-700/80 focus:border-cyan-500'
                    }`}
                  />
                </div>
                <button
                  type="button"
                  onClick={handleValidateInviteCode}
                  disabled={isValidatingCode || !inviteCode.trim() || isSubmitting}
                  className="px-4 py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold font-mono flex items-center gap-2 transition-colors shrink-0 shadow-sm cursor-pointer"
                >
                  {isValidatingCode ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Validating...</span>
                    </>
                  ) : (
                    <span>Validate</span>
                  )}
                </button>
              </div>
              <FieldError error={fieldErrors.invite_code} />
            </div>

            {/* Validation Outcome Banners */}
            {codeValidation?.isValid && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-300 text-xs font-mono flex items-center justify-between gap-2 animate-fadeIn">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>
                    ✓ Organization Found: <strong>{codeValidation.orgName}</strong>
                  </span>
                </div>
                <span className="text-[10px] text-emerald-400 uppercase tracking-widest font-bold">Verified</span>
              </div>
            )}
          </div>
        )}

        {/* ORG ADMIN SPECIFIC FIELDS: Organization Details */}
        {usageMode === 'ORGANIZATION' && orgSubMode === 'CREATE' && (
          <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl space-y-3">
            <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Building2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>Organization Details</span>
            </h3>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5 uppercase">
                Organization Name <span className="text-cyan-400">*</span>
              </label>
              <div className="relative">
                <Building2 className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => handleFieldChange('organization_name', setOrgName, e.target.value)}
                  placeholder="Apex Cybersecurity Inc."
                  disabled={isSubmitting}
                  className={`w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border rounded-lg text-sm text-slate-100 focus:outline-none transition-colors placeholder:text-slate-600 font-mono ${
                    fieldErrors.organization_name
                      ? 'border-red-500 focus:border-red-500'
                      : 'border-slate-700/80 focus:border-cyan-500'
                  }`}
                />
              </div>
              <FieldError error={fieldErrors.organization_name} />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1 uppercase">
                  Storage Quota (GB)
                </label>
                <div className="relative">
                  <HardDrive className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="number"
                    min={1}
                    max={10000}
                    value={storageQuotaGb}
                    onChange={(e) => setStorageQuotaGb(Math.max(1, parseInt(e.target.value) || 1))}
                    disabled={isSubmitting}
                    className="w-full pl-9 pr-3 py-2 bg-slate-900/80 border border-slate-700/80 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1 uppercase">
                  Max Workstations / Devices
                </label>
                <div className="relative">
                  <Cpu className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="number"
                    min={1}
                    max={1000}
                    value={maxDevices}
                    onChange={(e) => setMaxDevices(Math.max(1, parseInt(e.target.value) || 1))}
                    disabled={isSubmitting}
                    className="w-full pl-9 pr-3 py-2 bg-slate-900/80 border border-slate-700/80 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* COMMON FIELDS: Name, Email, Password */}
        {(usageMode === 'PERSONAL' ||
          (usageMode === 'ORGANIZATION' && orgSubMode === 'CREATE') ||
          (usageMode === 'ORGANIZATION' && orgSubMode === 'JOIN' && codeValidation?.isValid)) && (
          <div className="space-y-4 animate-fadeIn">
            {/* Full Name */}
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5 uppercase">
                {orgSubMode === 'CREATE' && usageMode === 'ORGANIZATION' ? 'Admin Full Name' : 'Full Name'}{' '}
                <span className="text-cyan-400">*</span>
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => handleFieldChange('full_name', setFullName, e.target.value)}
                  placeholder="Alexander Vance"
                  disabled={isSubmitting}
                  className={`w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border rounded-lg text-sm text-slate-100 focus:outline-none transition-colors placeholder:text-slate-600 font-mono ${
                    fieldErrors.full_name
                      ? 'border-red-500 focus:border-red-500'
                      : 'border-slate-700/80 focus:border-cyan-500'
                  }`}
                />
              </div>
              <FieldError error={fieldErrors.full_name} />
            </div>

            {/* Email Address */}
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5 uppercase">
                {usageMode === 'ORGANIZATION' ? 'Work Email Address' : 'Email Address'}{' '}
                <span className="text-cyan-400">*</span>
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => handleFieldChange('email', setEmail, e.target.value)}
                  placeholder="operator@company.com"
                  disabled={isSubmitting}
                  className={`w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border rounded-lg text-sm text-slate-100 focus:outline-none transition-colors placeholder:text-slate-600 font-mono ${
                    fieldErrors.email
                      ? 'border-red-500 focus:border-red-500'
                      : 'border-slate-700/80 focus:border-cyan-500'
                  }`}
                />
              </div>
              <FieldError error={fieldErrors.email} />
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5 uppercase">
                Master Encryption Password <span className="text-cyan-400">*</span>
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => handlePasswordChange(e.target.value)}
                  onFocus={() => setIsPasswordFocused(true)}
                  placeholder="••••••••••••"
                  disabled={isSubmitting}
                  className={`w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border rounded-lg text-sm text-slate-100 focus:outline-none transition-colors placeholder:text-slate-600 font-mono ${
                    fieldErrors.password
                      ? 'border-red-500 focus:border-red-500'
                      : 'border-slate-700/80 focus:border-cyan-500'
                  }`}
                />
              </div>
              <FieldError error={fieldErrors.password} />

              {/* Real-time Password Strength Meter */}
              <PasswordStrengthMeter
                strength={passwordStrength}
                visible={isPasswordFocused || password.length > 0}
              />
            </div>

            {/* Dynamic Submit Button */}
            <div className="pt-2">
              <AuthLoadingButton
                isLoading={isSubmitting}
                loadingText={
                  usageMode === 'PERSONAL'
                    ? 'Creating Account...'
                    : orgSubMode === 'CREATE'
                    ? 'Creating Organization...'
                    : 'Joining Organization...'
                }
                defaultText={
                  usageMode === 'PERSONAL'
                    ? 'Create Personal Account'
                    : orgSubMode === 'CREATE'
                    ? 'Create Organization & Admin'
                    : 'Join Organization as Employee'
                }
                icon={<ArrowRight className="w-4 h-4" />}
              />
            </div>
          </div>
        )}
      </form>

      <div className="mt-6 pt-6 border-t border-slate-800 text-center">
        <p className="text-xs text-slate-400">
          Already have an enrolled workstation or account?{' '}
          <Link to="/login" className="text-cyan-400 hover:underline font-medium">
            Sign In
          </Link>
        </p>
      </div>

      {/* Reusable Success Modal */}
      <AuthSuccessModal
        isOpen={successModal.isOpen}
        role={successModal.role}
        organizationName={successModal.orgName}
        inviteCode={successModal.inviteCode}
        onProceed={handleModalProceed}
      />
    </div>
  );
};
