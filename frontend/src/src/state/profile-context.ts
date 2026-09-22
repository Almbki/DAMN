import { createContext, useContext } from 'react';

import type { ProfileUpdateRequest, UserProfileRead, UserStateRead } from '@/api/types';

/**
 * 基础画像 + adaptive user state. Separate from the plan provider because the
 * profile is a small, independent slice; it still follows the same mock|api
 * switch (`EXPO_PUBLIC_DATA_SOURCE`).
 */
export type ProfileContextValue = {
  /** First load (or a manual refresh) is in flight. */
  loading: boolean;
  /** A save request is in flight. */
  saving: boolean;
  error: string | null;
  /** `null` = 尚未设置画像 (the backend returned 404). */
  profile: UserProfileRead | null;
  /** `null` while there is no profile yet. */
  state: UserStateRead | null;
  refresh: () => void;
  /** Resolves to `true` on success; the caller shows the "已保存" note. */
  save: (patch: ProfileUpdateRequest) => Promise<boolean>;
};

export const ProfileContext = createContext<ProfileContextValue | null>(null);

export function useProfile(): ProfileContextValue {
  const context = useContext(ProfileContext);
  if (!context) throw new Error('useProfile must be used inside <ProfileProvider>');
  return context;
}
