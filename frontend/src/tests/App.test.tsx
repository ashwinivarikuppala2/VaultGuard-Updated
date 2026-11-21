// @vitest-environment jsdom
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

describe('VaultGuard Application Routing & Foundation', () => {
  it('renders application authentication view by default when unauthenticated', () => {
    render(<App />);
    // The login page renders the VAULTGUARD brand heading as the unique h1.
    expect(screen.getByRole('heading', { name: /VAULTGUARD/i, level: 1 })).toBeInTheDocument();
  });
});

