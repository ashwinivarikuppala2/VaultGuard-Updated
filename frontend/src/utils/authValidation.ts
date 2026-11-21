/**
 * VaultGuard Authentication & Registration Validation Utilities
 */

export interface PasswordStrength {
  score: number; // 0 to 4
  label: 'Too Weak' | 'Weak' | 'Fair' | 'Good' | 'Strong';
  color: string;
  hasLength: boolean;
  hasUpper: boolean;
  hasLower: boolean;
  hasNumber: boolean;
  hasSpecial: boolean;
}

/**
 * Validate email format with standard email RFC regex
 */
export const validateEmail = (email: string): string | null => {
  const trimmed = email.trim();
  if (!trimmed) {
    return 'Please enter your email address.';
  }
  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
  if (!emailRegex.test(trimmed)) {
    return 'Please enter a valid email address.';
  }
  return null;
};

/**
 * Assess password strength and return validation error if invalid
 */
export const validatePassword = (password: string): { error: string | null; strength: PasswordStrength } => {
  const hasLength = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[^A-Za-z0-9]/.test(password);

  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if ((hasUpper && hasLower) || (hasNumber && hasSpecial)) score++;
  if (hasUpper && hasLower && hasNumber && hasSpecial) score++;

  let label: PasswordStrength['label'] = 'Too Weak';
  let color = 'bg-red-500';

  if (score === 1) {
    label = 'Weak';
    color = 'bg-orange-500';
  } else if (score === 2) {
    label = 'Fair';
    color = 'bg-amber-400';
  } else if (score === 3) {
    label = 'Good';
    color = 'bg-cyan-400';
  } else if (score >= 4) {
    label = 'Strong';
    color = 'bg-emerald-400';
  }

  const strength: PasswordStrength = {
    score,
    label,
    color,
    hasLength,
    hasUpper,
    hasLower,
    hasNumber,
    hasSpecial,
  };

  if (!password) {
    return { error: 'Password is required.', strength };
  }
  if (!hasLength) {
    return { error: 'Password must contain at least 8 characters.', strength };
  }

  return { error: null, strength };
};

/**
 * Validate full name
 */
export const validateFullName = (name: string): string | null => {
  const trimmed = name.trim();
  if (!trimmed) {
    return 'Full name is required.';
  }
  if (trimmed.length < 2) {
    return 'Name must contain at least 2 characters.';
  }
  return null;
};

/**
 * Validate organization name
 */
export const validateOrgName = (name: string): string | null => {
  const trimmed = name.trim();
  if (!trimmed) {
    return 'Organization name is required.';
  }
  if (trimmed.length < 2) {
    return 'Organization name must contain at least 2 characters.';
  }
  return null;
};

/**
 * Validate invite code format (e.g. VG-8XH2-LM9Q)
 */
export const validateInviteCodeFormat = (code: string): string | null => {
  const trimmed = code.trim().toUpperCase();
  if (!trimmed) {
    return 'Invitation code is required.';
  }
  if (!/^VG-[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(trimmed)) {
    return 'Invalid invitation code format. Expected format: VG-XXXX-XXXX.';
  }
  return null;
};

export interface ParsedError {
  message: string;
  fieldErrors: Record<string, string>;
  status?: number;
}

/**
 * Universal error parser for all HTTP status codes (400, 401, 403, 404, 409, 422, 429, 500)
 */
export const parseApiError = (err: any): ParsedError => {
  const fieldErrors: Record<string, string> = {};

  if (!err || !err.response) {
    // Network or client timeout error
    if (err?.message?.includes('Network Error') || err?.code === 'ERR_NETWORK') {
      return {
        message: 'Unable to connect to server. Please check your network connection.',
        fieldErrors,
        status: 0,
      };
    }
    return {
      message: err?.message || 'An unexpected error occurred. Please try again.',
      fieldErrors,
      status: 0,
    };
  }

  const status = err.response.status;
  const data = err.response.data;

  // Extract nested error message
  const rawMsg =
    data?.error?.message ||
    data?.message ||
    data?.detail ||
    (typeof data === 'string' ? data : null);

  switch (status) {
    case 400: {
      const msg = rawMsg || 'Bad request. Please review your input fields.';
      if (msg.toLowerCase().includes('invitation code is invalid') || msg.toLowerCase().includes('invalid invitation code')) {
        fieldErrors.invite_code = 'Invitation code is invalid.';
      } else if (msg.toLowerCase().includes('expired')) {
        fieldErrors.invite_code = 'Invitation code has expired.';
      } else if (msg.toLowerCase().includes('capacity') || msg.toLowerCase().includes('maximum employee limit')) {
        fieldErrors.invite_code = 'Organization has reached the maximum employee limit.';
      }
      return { message: msg, fieldErrors, status };
    }

    case 401: {
      const msg = rawMsg || 'Incorrect email or password.';
      return { message: msg, fieldErrors, status };
    }

    case 403: {
      const msg = rawMsg || 'Your account or organization has been disabled.';
      return { message: msg, fieldErrors, status };
    }

    case 404: {
      const msg = rawMsg || 'Requested resource was not found.';
      return { message: msg, fieldErrors, status };
    }

    case 409: {
      // Conflict, e.g. Duplicate email or org name
      let msg = rawMsg || 'A record with these details already exists.';
      if (msg.toLowerCase().includes('email') || data?.error?.details?.field === 'email') {
        fieldErrors.email = 'Email already exists. Please use a different address or sign in.';
        msg = 'Email already exists.';
      } else if (msg.toLowerCase().includes('name') || data?.error?.details?.field === 'name') {
        fieldErrors.organization_name = 'Organization name already exists.';
        msg = 'An organization with this name already exists.';
      }
      return { message: msg, fieldErrors, status };
    }

    case 422: {
      // Pydantic / FastAPI validation error
      let msg = 'Please fix the highlighted validation errors.';
      const details = data?.error?.details || data?.detail;
      if (Array.isArray(details)) {
        for (const item of details) {
          const fieldName = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : 'general';
          const fieldMsg = item.msg || 'Invalid field value.';
          if (fieldName === 'email') {
            fieldErrors.email = 'Please enter a valid email address.';
          } else if (fieldName === 'password') {
            fieldErrors.password = 'Password must contain at least 8 characters.';
          } else if (fieldName === 'full_name') {
            fieldErrors.full_name = 'Name must be at least 2 characters.';
          } else if (fieldName === 'organization_name') {
            fieldErrors.organization_name = 'Organization name must be at least 2 characters.';
          } else if (fieldName === 'invite_code') {
            fieldErrors.invite_code = 'Invitation code is invalid.';
          } else {
            fieldErrors[fieldName] = fieldMsg;
          }
        }
      }
      return { message: msg, fieldErrors, status };
    }

    case 429: {
      return {
        message: 'Too many requests. Please wait a moment and try again.',
        fieldErrors,
        status,
      };
    }

    case 500:
    default: {
      // Never expose raw stack traces or internal server error traces to users
      return {
        message: 'Unable to process your request at this time. Please try again later.',
        fieldErrors,
        status,
      };
    }
  }
};
