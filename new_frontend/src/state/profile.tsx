import { useCallback, useEffect, useMemo, useState } from 'react';

import { isApiError } from '@/api/client';
import { dataSource } from '@/api/config';
import { getMyProfile, updateMyProfile } from '@/api/endpoints';
import type { ProfileUpdateRequest, UserProfileRead, UserStateRead } from '@/api/types';
import { mockProfile, mockResetState, mockUserState } from '@/data/mock';
import { ProfileContext, type ProfileContextValue, type ProfileModelSnapshot } from '@/state/profile-context';
import { useSession } from '@/state/session';

type ProfileSnapshot = {
  profile: UserProfileRead | null;
  state: UserStateRead | null;
  model: ProfileModelSnapshot | null;
  error: string | null;
};

const NO_PROFILE: ProfileSnapshot = { profile: null, state: null, model: null, error: null };

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
      if (!identity) {
        // Mirrors the backend's 404: clearing the portrait leaves no profile.
        setProfile(null);
        setState(null);
      } else {
        setProfile({ identity });
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
    () => ({ loading: false, saving, error, profile, state, model: null, refresh: () => undefined, save }),
    [saving, error, profile, state, save],
  );

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

function ApiProfileProvider({ children }: { children: React.ReactNode }) {
  const session = useSession();
  const [profile, setProfile] = useState<UserProfileRead | null>(null);
  const [state, setState] = useState<UserStateRead | null>(null);
  const [model, setModel] = useState<ProfileModelSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apply = useCallback((next: ProfileSnapshot) => {
    setProfile(next.profile);
    setState(next.state);
    setModel(next.model);
    setError(next.error);
  }, []);

  /** 404 is not an error here — it means 尚未设置画像. */
  const fetchProfile = useCallback(async (): Promise<ProfileSnapshot> => {
    try {
      // `GET /users/me/profile` is FLAT: the static portrait and the adaptive
      // state live on one object. Re-nest it for the context's `{ profile,
      // state }` consumers.
      const flat = await getMyProfile();
      return {
        profile: {
          identity: flat.identity,
        },
        state: {
          duration_factor: flat.duration_factor,
          completion_prob: flat.completion_prob,
          stress_baseline: flat.stress_baseline,
          energy_drain_rate: flat.energy_drain_rate,
          proactive_score: flat.proactive_score,
          procrastination_tendency: flat.procrastination_tendency,
          preferred_time_slots: flat.preferred_time_slots,
          stress_response: flat.stress_response,
          state_energy: flat.state_energy,
          state_fatigue: flat.state_fatigue,
          state_stress: flat.state_stress,
          self_efficacy: flat.self_efficacy,
          update_count: flat.update_count,
          degraded: flat.degraded,
        },
        model: {
          trait: flat.trait ?? null,
          state: flat.state ?? null,
          metadata: flat.model_metadata ?? [],
        },
        error: null,
      };
    } catch (caught) {
      if (isApiError(caught) && caught.status === 404) return NO_PROFILE;
      return {
        profile: null,
        state: null,
        model: null,
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
    if (session.status === 'authenticated') refresh();
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
      loading: loading,
      saving,
      error,
      profile,
      state,
      model,
      refresh,
      save,
    }),
    [loading, saving, error, profile, state, model, refresh, save],
  );

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function ProfileProvider({ children }: { children: React.ReactNode }) {
  if (dataSource === 'api') return <ApiProfileProvider>{children}</ApiProfileProvider>;
  return <MockProfileProvider>{children}</MockProfileProvider>;
}

export { useProfile } from '@/state/profile-context';
