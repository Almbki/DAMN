import { describe, expect, it } from 'vitest';

import {
  authErrorMessage,
  demoLoginEnabled,
  resolveGuardState,
  validateEmail,
  validatePassword,
} from '@/domain/auth';

describe('demo credentials', () => {
  it('requires both email and password', () => {
    expect(demoLoginEnabled('demo@damn.app', 'password123')).toBe(true);
    expect(demoLoginEnabled('', 'password123')).toBe(false);
    expect(demoLoginEnabled('demo@damn.app', '')).toBe(false);
    expect(demoLoginEnabled('   ', 'password123')).toBe(false);
    expect(demoLoginEnabled(undefined, undefined)).toBe(false);
  });
});

describe('auth errors', () => {
  it('maps credential/conflict/network errors to product copy', () => {
    expect(authErrorMessage({ status: 401 }, 'login')).toContain('邮箱或密码');
    expect(authErrorMessage({ status: 409 }, 'register')).toContain('已经注册');
    expect(authErrorMessage({ status: 0 }, 'login')).toContain('连不上后端');
    expect(authErrorMessage({ status: 500, message: 'boom' }, 'login')).toBe('boom');
  });
});

describe('route guard', () => {
  it('boots, rejects, and requires onboarding for API users without Level 1', () => {
    expect(resolveGuardState({ status: 'booting', dataSource: 'api', hasTrait: false })).toBe(
      'booting',
    );
    expect(
      resolveGuardState({ status: 'unauthenticated', dataSource: 'api', hasTrait: false }),
    ).toBe('unauthenticated');
    expect(
      resolveGuardState({ status: 'authenticated', dataSource: 'api', hasTrait: false }),
    ).toBe('onboarding');
    expect(
      resolveGuardState({ status: 'authenticated', dataSource: 'api', hasTrait: true }),
    ).toBe('ready');
  });

  it('mock mode never enforces backend onboarding', () => {
    expect(
      resolveGuardState({ status: 'authenticated', dataSource: 'mock', hasTrait: false }),
    ).toBe('ready');
  });
});

describe('auth form validation', () => {
  it('validates email and password shape', () => {
    expect(validateEmail('a@b.com')).toBeNull();
    expect(validateEmail('')).not.toBeNull();
    expect(validateEmail('not-an-email')).not.toBeNull();
    expect(validatePassword('password123')).toBeNull();
    expect(validatePassword('short')).not.toBeNull();
  });
});