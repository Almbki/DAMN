import { useCallback, useEffect, useMemo, useState } from 'react';

import { isApiError } from '@/api/client';
import { dataSource } from '@/api/config';
import { getMyProfile, updateMyProfile } from '@/api/endpoints';
import type { ProfileUpdateRequest, UserProfileRead, UserStateRead } from '@/api/types';
import { mockProfile, mockResetState, mockUserState } from '@/data/mock';
import { ProfileContext, type ProfileContextValue } from '@/state/profile-context';
import { useSession } from '@/state/session';

type ProfileSnapshot = {
  profile: UserProfileRead | null;
  state: UserStateRead | null;
  error: string | null;
};

const NO_PROFILE: ProfileSnapshot = { profile: null, state: null, error: null };

function MockProfileProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<UserProfileRead | null>(mockProfile);
  const [state, setState] = useState<UserStateRead | null>(mockUserState);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = useCallback(async (patch: ProfileUpdateRequest) => {
    setSaving(true);
    try {
      // A short delay so the "保存中…" state is actually observable.
      await new Promise((resolve) => setTimeout(resolve, 220));
      const identity = patch.identity?.trim() ? patch.identity.trim() : null;
      const mbtiType = patch.mbti_type ?? null;
      if (!mbtiType && !identity) {
        // Mirrors the backend's 404: clearing both fields leaves no profile.
        setProfile(null);
        setState(null);
      } else {
        setProfile({
          mbti_type: mbtiType,
          mbti_dims: mbtiType ? (patch.mbti_dims ?? null) : null,
          identity,
        });
        setState(mockResetState());
      }
      setError(null);
      return true;
    } catch {
      setError('保存失败');
      return false;
    } finally {
      setSaving(false);
    }
  }, []);

  const value = useMemo<ProfileContextValue>(
    () => ({ loading: false, saving, error, profile, state, refresh: () => undefined, save }),
    [saving, error, profile, state, save],
  );

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

function ApiProfileProvider({ children }: { children: React.ReactNode }) {
  const session = useSession();
  const [profile, setProfile] = useState<UserProfileRead | null>(null);
  const [state, setState] = useState<UserStateRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apply = useCallback((next: ProfileSnapshot) => {
    setProfile(next.profile);
    setState(next.state);
    setError(next.error);
  }, []);

  /** 404 is not an error here — it means 尚未设置画像. */
  const fetchProfile = useCallback(async (): Promise<ProfileSnapshot> => {
    try {
      const response = await getMyProfile();
      return { profile: response.profile, state: response.state, error: null };
    } catch (caught) {
      if (isApiError(caught) && caught.status === 404) return NO_PROFILE;
      return {
        profile: null,
        state: null,
        error: isApiError(caught) ? caught.message : '读取画像失败',
      };
    }
  }, []);

  const refresh = useCallback(() => {
    setLoading(true);
    void fetchProfile().then((next) => {
      apply(next);
      setLoading(false);
    });
  }, [apply, fetchProfile]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch once the session is ready
    if (session.status === 'ready') refresh();
  }, [session.status, refresh]);

  const save = useCallback(
    async (patch: ProfileUpdateRequest) => {
      setSaving(true);
      try {
        await updateMyProfile(patch);
        // The PATCH re-initialises the state, so re-read it rather than guess.
        apply(await fetchProfile());
        return true;
      } catch (caught) {
        setError(isApiError(caught) ? caught.message : '保存失败');
        return false;
      } finally {
        setSaving(false);
      }
    },
    [apply, fetchProfile],
  );

  const value = useMemo<ProfileContextValue>(
    () => ({
      loading: loading || session.status === 'loading',
      saving,
      error,
      profile,
      state,
      refresh,
      save,
    }),
    [loading, session.status, saving, error, profile, state, refresh, save],
  );

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function ProfileProvider({ children }: { children: React.ReactNode }) {
  if (dataSource === 'api') return <ApiProfileProvider>{children}</ApiProfileProvider>;
  return <MockProfileProvider>{children}</MockProfileProvider>;
}

export { useProfile } from '@/state/profile-context';
