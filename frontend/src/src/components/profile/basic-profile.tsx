import { useCallback, useEffect, useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { UserProfileRead } from '@/api/types';
import { DimensionSlider } from '@/components/profile/dimension-slider';
import { MbtiPicker } from '@/components/profile/mbti-picker';
import { Button } from '@/components/ui/button';
import { FilterChip } from '@/components/ui/chip';
import { ErrorState, LoadingState } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { TextField } from '@/components/ui/text-field';
import { Line, Space, Type } from '@/constants/tokens';
import {
  MBTI_DIMENSIONS,
  clamp01,
  dimsForType,
  dimsFromPayload,
  explicitDims,
  normalizeMbti,
  resolveType,
  typeWithDimension,
  type MbtiDimension,
  type MbtiType,
  type MbtiWeights,
} from '@/domain/mbti';
import { useProfile } from '@/state/profile';
import { useTheme } from '@/state/theme';

type FormState = {
  type: MbtiType | null;
  dims: MbtiWeights | null;
  identity: string;
  /** Whether the optional per-dimension editor is expanded. */
  dimsOpen: boolean;
};

function seedForm(profile: UserProfileRead | null): FormState {
  const type = normalizeMbti(profile?.mbti_type);
  const dims = dimsFromPayload(type, profile?.mbti_dims);
  const hasDims = !!profile?.mbti_dims && Object.keys(profile.mbti_dims).length > 0;
  return {
    type: resolveType(type, dims),
    dims,
    identity: profile?.identity ?? '',
    dimsOpen: hasDims,
  };
}

/** 基础画像: MBTI type + optional dimension weights + an identity line. */
export function BasicProfileSection() {
  const { colors } = useTheme();
  const { loading, saving, error, profile, refresh, save } = useProfile();
  const [form, setForm] = useState<FormState>(() => seedForm(null));
  const [saved, setSaved] = useState(false);

  // Re-seed the form whenever the stored profile (re)loads.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- seed the form from the fetched profile
    setForm(seedForm(profile));
  }, [profile]);

  useEffect(() => {
    if (!saved) return;
    const timer = setTimeout(() => setSaved(false), 2500);
    return () => clearTimeout(timer);
  }, [saved]);

  const pickType = useCallback((next: MbtiType) => {
    setForm((prev) => ({ ...prev, type: next, dims: dimsForType(next) }));
    setSaved(false);
  }, []);

  const clearType = useCallback(() => {
    setForm((prev) => ({ ...prev, type: null, dims: null, dimsOpen: false }));
    setSaved(false);
  }, []);

  const toggleDims = useCallback(() => {
    setForm((prev) => ({
      ...prev,
      dims: prev.dims ?? (prev.type ? dimsForType(prev.type) : null),
      dimsOpen: !prev.dimsOpen,
    }));
    setSaved(false);
  }, []);

  const changeDim = useCallback((dimension: MbtiDimension, weight: number) => {
    setForm((prev) => {
      const base = prev.dims ?? (prev.type ? dimsForType(prev.type) : null);
      if (!base || !prev.type) return prev;
      const dims = { ...base, [dimension]: clamp01(weight) };
      return { ...prev, dims, type: typeWithDimension(prev.type, dimension, dims[dimension]) };
    });
    setSaved(false);
  }, []);

  const changeIdentity = useCallback((identity: string) => {
    setForm((prev) => ({ ...prev, identity }));
    setSaved(false);
  }, []);

  const payload = useMemo(() => {
    const rawDims = form.type && form.dimsOpen ? form.dims : null;
    const trimmed = form.identity.trim();
    return {
      mbti_type: form.type,
      mbti_dims: explicitDims(form.type, rawDims),
      identity: trimmed ? trimmed : null,
    };
  }, [form]);

  const dirty = useMemo(() => {
    const storedType = normalizeMbti(profile?.mbti_type);
    const storedHasDims = !!profile?.mbti_dims && Object.keys(profile.mbti_dims).length > 0;
    const storedDims = storedHasDims
      ? explicitDims(storedType, dimsFromPayload(storedType, profile?.mbti_dims))
      : null;
    const stored = {
      mbti_type: storedType,
      mbti_dims: storedDims,
      identity: profile?.identity ?? null,
    };
    return JSON.stringify(payload) !== JSON.stringify(stored);
  }, [payload, profile]);

  const onSave = useCallback(async () => {
    const ok = await save(payload);
    if (ok) setSaved(true);
  }, [save, payload]);

  const activeType = form.type;
  const showDims = activeType != null && form.dimsOpen;

  return (
    <View style={styles.section}>
      <Text style={[styles.title, { color: colors.ink }]}>基础画像</Text>
      <Text style={[styles.body, { color: colors.inkMuted }]}>
        系统用它来预估你的用时和完成概率。可以随时改，改完立即生效。
      </Text>

      {loading ? (
        <LoadingState label="正在读取画像…" />
      ) : error ? (
        <ErrorState title="画像读取失败" body={error} onRetry={refresh} />
      ) : (
        <Surface level="level1" radius="lg">
          <View style={styles.card}>
            {profile == null ? (
              <Text style={[styles.body, { color: colors.inkMuted }]}>
                尚未设置画像。选一个 MBTI 类型，或者只填身份也可以。
              </Text>
            ) : null}

            <View style={styles.field}>
              <Text style={[styles.fieldLabel, { color: colors.inkMuted }]}>MBTI 类型</Text>
              <MbtiPicker value={form.type} onChange={pickType} />
              <View style={styles.skipRow}>
                <FilterChip label="未知 / 跳过" selected={form.type == null} onPress={clearType} />
              </View>
            </View>

            {activeType ? (
              <View style={styles.field}>
                <View style={styles.fieldHead}>
                  <Text style={[styles.fieldLabel, { color: colors.inkMuted }]}>维度微调（可选）</Text>
                  <Button
                    label={form.dimsOpen ? '收起' : '展开'}
                    variant="text"
                    size="sm"
                    icon={form.dimsOpen ? 'chevronDown' : 'chevronRight'}
                    onPress={toggleDims}
                  />
                </View>
                {showDims ? (
                  <View style={styles.sliders}>
                    {MBTI_DIMENSIONS.map((dimension) => (
                      <DimensionSlider
                        key={dimension}
                        dimension={dimension}
                        value={form.dims?.[dimension] ?? dimsForType(activeType)[dimension]}
                        onChange={(weight) => changeDim(dimension, weight)}
                      />
                    ))}
                    <Text style={[styles.helper, { color: colors.inkFaint }]}>
                      不确定就保持默认，系统按你选的整体类型来算。
                    </Text>
                  </View>
                ) : (
                  <Text style={[styles.helper, { color: colors.inkFaint }]}>
                    默认按 {activeType} 的通用模板，展开可以逐维调整。
                  </Text>
                )}
              </View>
            ) : null}

            <View style={styles.field}>
              <TextField
                label="身份 / 角色"
                value={form.identity}
                onChangeText={changeIdentity}
                placeholder="大学生 / 开发者"
              />
            </View>

            <View style={styles.actions}>
              <Button
                label={saving ? '保存中…' : '保存'}
                variant="filled"
                disabled={saving || !dirty}
                onPress={() => {
                  void onSave();
                }}
              />
              {saved ? (
                <Text style={[styles.saved, { color: colors.inkMuted }]}>已保存</Text>
              ) : null}
            </View>
          </View>
        </Surface>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    gap: Space.md,
  },
  title: {
    fontSize: Type.titleLarge,
    fontWeight: '600',
  },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 600,
  },
  card: {
    padding: Space.xl,
    gap: Space.xl,
  },
  field: {
    gap: Space.md,
  },
  fieldHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  fieldLabel: {
    fontSize: Type.labelMedium,
  },
  skipRow: {
    flexDirection: 'row',
  },
  sliders: {
    gap: Space.lg,
  },
  helper: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.normal,
    maxWidth: 520,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.lg,
  },
  saved: {
    fontSize: Type.labelMedium,
  },
});
