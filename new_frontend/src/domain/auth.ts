/** Pure auth helpers (testable without React Native). */

export type SessionStatus = 'booting' | 'unauthenticated' | 'authenticated' | 'error';

export type GuardState =
  | 'booting'
  | 'error'
  | 'unauthenticated'
  | 'onboarding'
  | 'ready';

/**
 * Central route-guard state machine.
 *
 * Demo auto-login is not a fifth auth state: it produces a normal
 * ``authenticated`` session. Mock mode never enforces backend onboarding.
 */
export function resolveGuardState(input: {
  status: SessionStatus;
  dataSource: 'api' | 'mock';
  hasTrait: boolean;
}): GuardState {
  if (input.status === 'booting') return 'booting';
  if (input.status === 'error') return 'error';
  if (input.status === 'unauthenticated') return 'unauthenticated';
  if (input.dataSource === 'mock') return 'ready';
  return input.hasTrait ? 'ready' : 'onboarding';
}

export function demoLoginEnabled(
  email: string | null | undefined,
  password: string | null | undefined,
): boolean {
  return Boolean(email?.trim() && password);
}

type ErrorLike = { status?: number; message?: string; code?: string };

export function authErrorMessage(
  error: unknown,
  mode: 'login' | 'register',
): string {
  const value = error as ErrorLike | null;
  if (typeof value?.status === 'number') {
    if (value.status === 0) return '连不上后端，检查网络或 API 地址。';
    if (value.status === 401) return '邮箱或密码不正确。';
    if (value.status === 409) return '这个邮箱已经注册过了。';
    if (value.status === 422) return '请检查邮箱和密码格式。';
  }
  return (
    value?.message ??
    (mode === 'login' ? '登录失败，请稍后再试。' : '注册失败，请稍后再试。')
  );
}

export function validateEmail(value: string): string | null {
  const email = value.trim();
  if (!email) return '请填写邮箱。';
  if (!email.includes('@') || email.startsWith('@') || email.endsWith('@')) {
    return '邮箱格式不正确。';
  }
  return null;
}

export function validatePassword(value: string): string | null {
  if (value.length < 8) return '密码至少 8 位。';
  return null;
}