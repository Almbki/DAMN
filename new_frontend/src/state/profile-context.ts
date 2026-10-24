import { createContext, useContext } from 'react';

import type {
  DynamicStateSnapshot,
  ModelMetadata,
  ProfileUpdateRequest,
  TraitSnapshot,
  UserProfileRead,
  UserStateRead,
} from '@/api/types';

/** Authoritative three-layer model snapshots; presentation-only consumers. */
export type ProfileModelSnapshot = {
  trait: TraitSnapshot | null;
  state: DynamicStateSnapshot | null;
  metadata: ModelMetadata[];
};

/**
 * 基础画像 + compatibility state + the real Level 1/2 snapshots. Separate from
 * the plan provider because the profile is a small, independent slice; it still
 * follows the same mock|api switch (`EXPO_PUBLIC_DATA_SOURCE`).
 */
export type ProfileContextValue = {
  /** First load (or a manual refresh) is in flight. */
  loading: boolean;
  /** A save request is in flight. */
  saving: boolean;
  error: string | null;
  /** `null` = 尚未设置画像 (the backend returned 404). */
  profile: UserProfileRead | null;
  /** Compatibility projections only; do not use as the product state. */
  state: UserStateRead | null;
  /** Real Level 1 trait + Level 2 state snapshots. */
  model: ProfileModelSnapshot | null;
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
