import { StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import type { UserStateRead } from '@/api/types';
import { Progress } from '@/components/ui/progress';
import { ErrorState, LoadingState } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import { chunk } from '@/domain/mbti';
import { useProfile } from '@/state/profile';
import { useTheme } from '@/state/theme';

type Tile = {
  key: string;
  label: string;
  value: string;
  unit: string;
  /** `0..1` bar value; `null` for unitless counters with no natural bar. */
  ratio: number | null;
  note: string;
};

/** Compute columns from the real window because `flexWrap` is unreliable on web. */
function columnsFor(width: number): number {
  return width >= 760 ? 3 : 2;
}

function percent(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}

/** Honor the explicit flag and the documented rule behind it. */
function isDegraded(state: UserStateRead): boolean {
  return state.degraded || state.update_count < 3;
}

function levelNote(ratio: number, label: string): string {
  if (ratio >= 0.6) return `${label}偏高`;
  if (ratio <= 0.4) return `${label}偏低`;
  return `${label}中等`;
}

function buildTiles(state: UserStateRead): Tile[] {
  const degraded = isDegraded(state);
  const remaining = Math.max(0, 3 - state.update_count);
  return [
    {
      key: 'energy',
      label: '当前精力',
      value: percent(state.state_energy),
      unit: '',
      ratio: state.state_energy,
      note: levelNote(state.state_energy, '精力'),
    },
    {
      key: 'efficacy',
      label: '自我效能',
      value: percent(state.self_efficacy),
      unit: '',
      ratio: state.self_efficacy,
      note: levelNote(state.self_efficacy, '效能'),
    },
    {
      key: 'duration',
      label: '用时系数',
      value: state.duration_factor.toFixed(2),
      unit: '×',
      ratio: null,
      note: `实际用时约为预估的 ${Math.round(state.duration_factor * 100)}%`,
    },
    {
      key: 'completion',
      label: '完成概率',
      value: percent(state.completion_prob),
      unit: '',
      ratio: state.completion_prob,
      note: state.completion_prob >= 0.7 ? '偏稳' : state.completion_prob <= 0.4 ? '偏低' : '中等',
    },
    {
      key: 'stress',
      label: '压力基线',
      value: percent(state.stress_baseline),
      unit: '',
      ratio: state.stress_baseline,
      note: levelNote(state.stress_baseline, '压力'),
    },
    {
      key: 'updates',
      label: '反馈次数',
      value: `${state.update_count}`,
      unit: '次',
      ratio: null,
      note: degraded ? `还需要 ${remaining} 次反馈` : '已进入稳定校准',
    },
  ];
}

/** 状态仪表盘: the feedback-updated user-model numbers behind plan generation. */
export function StateDashboardSection() {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const { loading, error, state, refresh } = useProfile();

  const columns = columnsFor(width > 0 ? width : 0);
  const rows = state ? chunk(buildTiles(state), columns) : [];

  return (
    <View style={styles.section}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: colors.ink }]}>状态仪表盘</Text>
        {state && isDegraded(state) ? (
          <View style={[styles.badge, { backgroundColor: colors.surfaceContainerHigh }]}>
            <View style={[styles.badgeDot, { backgroundColor: colors.warning }]} />
            <Text style={[styles.badgeText, { color: colors.inkMuted }]}>冷启动校准中</Text>
          </View>
        ) : null}
      </View>
      <Text style={[styles.body, { color: colors.inkMuted }]}>
        一组会随反馈更新的用户模型数字，用来预估用时和完成概率。不是评分，只是系统当下的判断。
      </Text>

      {loading ? (
        <LoadingState label="正在读取状态…" />
      ) : error ? (
        <ErrorState title="状态读取失败" body={error} onRetry={refresh} />
      ) : state == null ? (
        <Surface level="level0" radius="lg" bordered>
          <View style={styles.empty}>
            <Text style={[styles.body, { color: colors.inkMuted }]}>
              还没有状态数据。设置画像或完成一次反馈后，这里会出现数字。
            </Text>
          </View>
        </Surface>
      ) : (
        <View style={styles.rows}>
          {rows.map((row) => (
            <View key={row[0].key} style={styles.row}>
              {row.map((tile) => (
                <StateTile key={tile.key} tile={tile} />
              ))}
              {Array.from({ length: columns - row.length }).map((_, index) => (
                <View key={`spacer-${index}`} style={styles.spacer} />
              ))}
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

function StateTile({ tile }: { tile: Tile }) {
  const { colors } = useTheme();
  return (
    <Surface level="level1" radius="lg" style={styles.tile}>
      <View style={styles.tileInner}>
        <Text style={[styles.tileLabel, { color: colors.inkMuted }]}>{tile.label}</Text>
        <View style={styles.valueRow}>
          <Text style={[styles.tileValue, { color: colors.ink }]}>{tile.value}</Text>
          {tile.unit ? (
            <Text style={[styles.tileUnit, { color: colors.inkMuted }]}>{tile.unit}</Text>
          ) : null}
        </View>
        {tile.ratio == null ? (
          <View style={styles.barSpacer} />
        ) : (
          <Progress value={tile.ratio} height={4} color={colors.inkMuted} />
        )}
        <Text style={[styles.tileNote, { color: colors.inkFaint }]}>{tile.note}</Text>
      </View>
    </Surface>
  );
}

const styles = StyleSheet.create({
  section: {
    gap: Space.md,
  },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  title: {
    fontSize: Type.titleLarge,
    fontWeight: '600',
  },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
    borderRadius: 999,
    paddingHorizontal: Space.md,
    paddingVertical: Space.xs,
  },
  badgeDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  badgeText: {
    fontSize: Type.labelSmall,
  },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 600,
  },
  empty: {
    padding: Space.xl,
  },
  rows: {
    gap: Space.md,
  },
  row: {
    flexDirection: 'row',
    gap: Space.md,
  },
  tile: {
    flex: 1,
    minWidth: 0,
  },
  spacer: {
    flex: 1,
    minWidth: 0,
  },
  tileInner: {
    padding: Space.lg,
    gap: Space.sm,
  },
  tileLabel: {
    fontSize: Type.labelMedium,
  },
  valueRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Space.xs,
  },
  tileValue: {
    fontFamily: Fonts.mono,
    fontSize: Type.displaySmall,
    lineHeight: Type.displaySmall * 1.05,
  },
  tileUnit: {
    fontSize: Type.labelMedium,
    paddingBottom: 6,
  },
  barSpacer: {
    height: 4,
  },
  tileNote: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.normal,
  },
});
