import { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { isApiError } from '@/api/client';
import {
  archiveGoal,
  archiveGoalSet,
  attachGoalsToSet,
  createGoalSet,
  getGoalSet,
  listGoalSets,
  listGoals,
  restoreGoal,
  restoreGoalSet,
} from '@/api/endpoints';
import type {
  GoalDetailRead,
  GoalLifecycleImpact,
  GoalSetDetailRead,
  GoalSetRead,
  GoalSetStatus,
  GoalStatus,
} from '@/api/types';
import { BottomSheet } from '@/components/ui/bottom-sheet';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { FilterChip } from '@/components/ui/chip';
import { Dialog } from '@/components/ui/dialog';
import { useInteraction } from '@/components/ui/interaction';
import {
  EmptyState,
  ErrorState,
  InlineNotice,
  LoadingState,
} from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { TextField } from '@/components/ui/text-field';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { formatShort, parseISO } from '@/domain/date';
import {
  GOAL_SET_FILTERS,
  canAttachGoals,
  filterGoalSets,
  goalSetCountsLabel,
  goalSetFilterCounts,
  goalSetStatusLabel,
  type GoalSetFilter,
} from '@/domain/goal-set';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

type Notice = { tone: 'error' | 'info' | 'success'; message: string };

const GOAL_STATUS_LABEL: Record<GoalStatus, string> = {
  draft: '待拆解',
  active: '进行中',
  completed: '已完成',
  archived: '已归档',
  cancelled: '已取消',
};

function errorMessage(caught: unknown, fallback: string): string {
  if (isApiError(caught)) return caught.message;
  if (caught instanceof Error && caught.message) return caught.message;
  return fallback;
}

function formatCreatedAt(value: string): string {
  if (!value) return '—';
  const date = parseISO(value);
  return `${date.getFullYear()} 年 ${date.getMonth() + 1} 月 ${date.getDate()} 日`;
}

function goalImpactMessage(
  restoring: boolean,
  title: string,
  impact: GoalLifecycleImpact,
): string {
  if (restoring) {
    return impact.restored_tasks != null
      ? `「${title}」已恢复，带回 ${impact.restored_tasks} 个任务。`
      : `「${title}」已恢复。`;
  }
  return impact.removed_tasks != null
    ? `「${title}」已归档，移除 ${impact.removed_tasks} 个未完成任务，已完成任务和执行记录已保留。`
    : `「${title}」已归档。`;
}

export default function GoalSetsScreen() {
  const { colors } = useTheme();
  const { mode, refresh } = usePlan();
  const isApi = mode === 'api';

  const [sets, setSets] = useState<GoalSetRead[]>([]);
  const [filter, setFilter] = useState<GoalSetFilter>('active');
  const [loading, setLoading] = useState(isApi);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<GoalSetDetailRead | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailNonce, setDetailNonce] = useState(0);
  const [goalBusyId, setGoalBusyId] = useState<number | null>(null);
  const [setBusy, setSetBusy] = useState(false);

  const [attachOpen, setAttachOpen] = useState(false);
  const [attachLoading, setAttachLoading] = useState(false);
  const [attachBusy, setAttachBusy] = useState(false);
  const [attachError, setAttachError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<GoalDetailRead[]>([]);
  const [selectedGoalIds, setSelectedGoalIds] = useState<Set<number>>(() => new Set());
  const [archiveOpen, setArchiveOpen] = useState(false);

  const loadSets = useCallback(async () => {
    try {
      const next = await listGoalSets(true);
      setSets(next);
      setError(null);
    } catch (caught) {
      setError(errorMessage(caught, '加载目标集失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isApi) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async fetch when the screen mounts
    void loadSets();
  }, [isApi, loadSets]);

  useEffect(() => {
    if (selectedId == null) return;
    let cancelled = false;
    void (async () => {
      try {
        const next = await getGoalSet(selectedId);
        if (!cancelled) {
          setDetail(next);
          setDetailError(null);
        }
      } catch (caught) {
        if (!cancelled) setDetailError(errorMessage(caught, '加载目标集详情失败'));
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId, detailNonce]);

  const counts = goalSetFilterCounts(sets);
  const filtered = filterGoalSets(sets, filter);

  function openSet(id: number) {
    setNotice(null);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    setSelectedId(id);
  }

  function closeDetail() {
    setSelectedId(null);
  }

  function openCreate() {
    setCreateName('');
    setCreateDescription('');
    setCreateError(null);
    setCreateOpen(true);
  }

  async function submitCreate() {
    const name = createName.trim();
    if (!name) return;
    setCreateBusy(true);
    setCreateError(null);
    try {
      const created = await createGoalSet({
        name,
        description: createDescription.trim() || null,
      });
      setCreateOpen(false);
      setCreateName('');
      setCreateDescription('');
      setFilter('active');
      setNotice({ tone: 'success', message: `已创建「${created.name}」。` });
      await loadSets();
    } catch (caught) {
      setCreateError(errorMessage(caught, '创建目标集失败'));
    } finally {
      setCreateBusy(false);
    }
  }

  async function toggleGoal(goal: GoalDetailRead) {
    setGoalBusyId(goal.id);
    setNotice(null);
    const restoring = goal.status === 'archived';
    try {
      const impact = restoring ? await restoreGoal(goal.id) : await archiveGoal(goal.id);
      setNotice({ tone: 'success', message: goalImpactMessage(restoring, goal.title, impact) });
      await loadSets();
      setDetailNonce((value) => value + 1);
      refresh();
    } catch (caught) {
      setNotice({ tone: 'error', message: errorMessage(caught, '操作没有完成') });
    } finally {
      setGoalBusyId(null);
    }
  }

  async function openAttach() {
    if (!detail) return;
    const inSet = new Set(detail.goals.map((goal) => goal.id));
    setAttachOpen(true);
    setSelectedId(null);
    setAttachLoading(true);
    setAttachError(null);
    setSelectedGoalIds(new Set());
    try {
      const all = await listGoals(undefined, { includeArchived: false });
      setCandidates(
        all.filter(
          (goal) =>
            goal.status === 'active' && goal.goal_set_id == null && !inSet.has(goal.id),
        ),
      );
    } catch (caught) {
      setAttachError(errorMessage(caught, '加载可添加的目标失败'));
      setCandidates([]);
    } finally {
      setAttachLoading(false);
    }
  }

  function cancelAttach() {
    setAttachOpen(false);
    if (detail) setSelectedId(detail.id);
  }

  function toggleGoalSelection(id: number) {
    setSelectedGoalIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function submitAttach() {
    if (!detail || selectedGoalIds.size === 0) return;
    const setId = detail.id;
    const setName = detail.name;
    setAttachBusy(true);
    setAttachError(null);
    try {
      const result = await attachGoalsToSet(setId, Array.from(selectedGoalIds));
      setAttachOpen(false);
      setNotice({
        tone: 'success',
        message: `已添加 ${result.attached_goals} 个目标到「${setName}」。`,
      });
      await loadSets();
      setDetail(null);
      setDetailError(null);
      setDetailLoading(true);
      setDetailNonce((value) => value + 1);
      setSelectedId(setId);
    } catch (caught) {
      setAttachError(errorMessage(caught, '添加目标失败'));
    } finally {
      setAttachBusy(false);
    }
  }

  function openArchiveConfirm() {
    if (!detail) return;
    setArchiveOpen(true);
    setSelectedId(null);
  }

  function cancelArchive() {
    setArchiveOpen(false);
    if (detail) setSelectedId(detail.id);
  }

  async function confirmArchive() {
    if (!detail) return;
    const setId = detail.id;
    const setName = detail.name;
    setSetBusy(true);
    try {
      const impact = await archiveGoalSet(setId);
      setArchiveOpen(false);
      setNotice({
        tone: 'success',
        message: `已归档「${setName}」：${impact.archived_goals} 个目标归档，移除 ${impact.removed_tasks} 个未完成任务，保留 ${impact.preserved_completed_tasks} 个已完成任务。`,
      });
      await loadSets();
      refresh();
      setDetail(null);
      setDetailError(null);
      setDetailLoading(true);
      setDetailNonce((value) => value + 1);
      setSelectedId(setId);
    } catch (caught) {
      setArchiveOpen(false);
      setNotice({ tone: 'error', message: errorMessage(caught, '归档目标集失败') });
      setSelectedId(setId);
    } finally {
      setSetBusy(false);
    }
  }

  async function restoreSet() {
    if (!detail) return;
    const setId = detail.id;
    const setName = detail.name;
    setSetBusy(true);
    setNotice(null);
    try {
      const impact = await restoreGoalSet(setId);
      setNotice({
        tone: 'success',
        message: `已恢复「${setName}」：${impact.restored_goals} 个目标，${impact.restored_tasks} 个任务。`,
      });
      await loadSets();
      refresh();
      setDetailNonce((value) => value + 1);
    } catch (caught) {
      setNotice({ tone: 'error', message: errorMessage(caught, '恢复目标集失败') });
    } finally {
      setSetBusy(false);
    }
  }

  const emptyTitle =
    filter === 'archived'
      ? '还没有已归档的目标集'
      : filter === 'active'
        ? '还没有进行中的目标集'
        : '还没有目标集';
  const emptyBody =
    filter === 'archived'
      ? '归档后的目标集会出现在这里，可以随时恢复。'
      : '新建一个目标集，把同一类目标放在一起；生成计划时会更容易挑选。';

  return (
    <View style={styles.page}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <View style={styles.headerRow}>
            <View style={styles.headerCopy}>
              <Text style={[styles.title, { color: colors.ink }]}>目标集</Text>
              <Text style={[styles.body, { color: colors.inkMuted }]}>
                把同一类目标放在一起，归档时整组处理；已完成的任务和执行记录都会保留。
              </Text>
            </View>
            {isApi ? (
              <Button label="新建目标集" icon="plus" variant="filled" onPress={openCreate} />
            ) : null}
          </View>
        </View>

        {notice ? (
          <InlineNotice
            message={notice.message}
            tone={notice.tone}
            onDismiss={() => setNotice(null)}
          />
        ) : null}

        {error && sets.length > 0 ? (
          <InlineNotice message={error} onDismiss={() => setError(null)} />
        ) : null}

        {!isApi ? (
          <EmptyState
            title="目标集需要连接后端"
            body="目标集保存在后端；演示模式只在本机保存任务，无法管理目标集。"
          />
        ) : (
          <>
            <View style={styles.filterRow}>
              {GOAL_SET_FILTERS.map((item) => (
                <FilterChip
                  key={item.key}
                  label={item.label}
                  selected={filter === item.key}
                  count={counts[item.key]}
                  onPress={() => setFilter(item.key)}
                />
              ))}
            </View>

            {loading && sets.length === 0 ? (
              <LoadingState label="正在加载目标集…" />
            ) : error && sets.length === 0 ? (
              <ErrorState
                title="加载目标集失败"
                body={error}
                onRetry={() => {
                  setLoading(true);
                  void loadSets();
                }}
              />
            ) : filtered.length === 0 ? (
              <EmptyState
                title={emptyTitle}
                body={emptyBody}
                actionLabel={filter === 'archived' ? undefined : '新建目标集'}
                actionIcon="plus"
                onAction={filter === 'archived' ? undefined : openCreate}
              />
            ) : (
              <View style={styles.list}>
                {filtered.map((set) => (
                  <GoalSetCard key={set.id} set={set} onPress={() => openSet(set.id)} />
                ))}
              </View>
            )}
          </>
        )}
      </ScrollView>

      <Dialog
        visible={createOpen}
        title="新建目标集"
        description="给一组相关的目标起个名字。之后生成计划时，可以只挑这个目标集里的目标。"
        closable={!createBusy}
        onRequestClose={() => {
          if (!createBusy) setCreateOpen(false);
        }}
        actions={[
          {
            label: '取消',
            variant: 'text',
            disabled: createBusy,
            onPress: () => setCreateOpen(false),
          },
          {
            label: createBusy ? '创建中…' : '创建',
            variant: 'filled',
            disabled: createBusy || createName.trim().length === 0,
            onPress: () => void submitCreate(),
          },
        ]}>
        <TextField
          label="名称"
          value={createName}
          onChangeText={setCreateName}
          placeholder="例如：期末复习"
          autoFocus
          background={colors.surfaceContainerLowest}
        />
        <TextField
          label="描述（选填）"
          value={createDescription}
          onChangeText={setCreateDescription}
          placeholder="这组目标要解决什么？"
          multiline
          background={colors.surfaceContainerLowest}
        />
        {createError ? (
          <InlineNotice message={createError} onDismiss={() => setCreateError(null)} />
        ) : null}
      </Dialog>

      <BottomSheet
        visible={selectedId != null}
        title={detail?.name ?? '目标集'}
        subtitle={
          detail
            ? `${goalSetStatusLabel(detail.status)} · ${goalSetCountsLabel(detail)}`
            : '正在加载…'
        }
        onClose={closeDetail}
        footer={
          <>
            <Button label="关闭" variant="text" onPress={closeDetail} />
            {detail ? (
              detail.status === 'archived' ? (
                <Button
                  label={setBusy ? '恢复中…' : '恢复目标集'}
                  variant="filled"
                  disabled={setBusy}
                  onPress={() => void restoreSet()}
                />
              ) : (
                <>
                  <Button
                    label="添加目标"
                    variant="tonal"
                    icon="plus"
                    disabled={!canAttachGoals(detail.status) || setBusy}
                    onPress={() => void openAttach()}
                  />
                  <Button
                    label="归档目标集"
                    variant="outlined"
                    disabled={setBusy}
                    onPress={openArchiveConfirm}
                  />
                </>
              )
            ) : null}
          </>
        }>
        {notice ? (
          <InlineNotice
            message={notice.message}
            tone={notice.tone}
            onDismiss={() => setNotice(null)}
          />
        ) : null}

        {detailLoading && !detail ? <LoadingState label="正在加载目标集…" /> : null}

        {detailError ? (
          <ErrorState
            title="加载目标集失败"
            body={detailError}
            onRetry={() => {
              setDetailError(null);
              setDetailLoading(true);
              setDetailNonce((value) => value + 1);
            }}
          />
        ) : null}

        {detail ? (
          <>
            <View style={styles.detailSummary}>
              <View style={styles.detailHead}>
                <Text style={[styles.detailName, { color: colors.ink }]}>{detail.name}</Text>
                <StatusBadge status={detail.status} />
              </View>
              {detail.description ? (
                <Text style={[styles.body, { color: colors.inkMuted }]}>
                  {detail.description}
                </Text>
              ) : null}
              <View style={styles.cardMeta}>
                <Text style={[styles.metaText, { color: colors.inkMuted }]}>
                  {goalSetCountsLabel(detail)}
                </Text>
                <Text style={[styles.createdText, { color: colors.inkFaint }]}>
                  创建于 {formatCreatedAt(detail.created_at)}
                </Text>
              </View>
            </View>

            {detail.status === 'archived' ? (
              <Surface level="level0" radius="md" bordered>
                <View style={styles.archivedNote}>
                  <Text style={[styles.noteText, { color: colors.inkMuted }]}>
                    这个目标集已归档，里面的目标不会参与新的计划生成。恢复后可以继续使用。
                  </Text>
                </View>
              </Surface>
            ) : null}

            <View style={styles.sectionHead}>
              <Text style={[styles.sectionTitle, { color: colors.ink }]}>包含的目标</Text>
              <Text style={[styles.counter, { color: colors.inkMuted }]}>
                {detail.goals.length}
              </Text>
            </View>

            {detail.goals.length === 0 ? (
              <Surface level="level0" radius="lg" bordered style={{ borderStyle: 'dashed' }}>
                <View style={styles.emptyGoals}>
                  <Text style={[styles.emptyTitle, { color: colors.ink }]}>还没有目标</Text>
                  <Text style={[styles.noteText, { color: colors.inkMuted }]}>
                    {canAttachGoals(detail.status)
                      ? '把已经存在、还没归组的目标加进来。'
                      : '这个目标集里没有目标。恢复目标集后可以继续添加。'}
                  </Text>
                </View>
              </Surface>
            ) : (
              <View style={styles.goalList}>
                {detail.goals.map((goal) => (
                  <GoalRow
                    key={goal.id}
                    goal={goal}
                    busy={goalBusyId === goal.id}
                    disabled={goalBusyId != null}
                    onToggle={() => void toggleGoal(goal)}
                  />
                ))}
              </View>
            )}
          </>
        ) : null}
      </BottomSheet>

      <Dialog
        visible={attachOpen}
        width={560}
        title="添加目标"
        description={
          detail
            ? `把还没归组的目标加进「${detail.name}」。已经在别的目标集里的目标不会出现在这里。`
            : '选择要加入的目标。'
        }
        closable={!attachBusy}
        onRequestClose={cancelAttach}
        actions={[
          {
            label: '取消',
            variant: 'text',
            disabled: attachBusy,
            onPress: cancelAttach,
          },
          {
            label: attachBusy
              ? '添加中…'
              : `添加${selectedGoalIds.size > 0 ? ` ${selectedGoalIds.size} 个` : ''}`,
            variant: 'filled',
            disabled: attachBusy || selectedGoalIds.size === 0,
            onPress: () => void submitAttach(),
          },
        ]}>
        {attachLoading ? <LoadingState label="正在查找可添加的目标…" /> : null}
        {attachError ? (
          <InlineNotice message={attachError} onDismiss={() => setAttachError(null)} />
        ) : null}
        {!attachLoading && !attachError && candidates.length === 0 ? (
          <Text style={[styles.noteText, { color: colors.inkMuted }]}>
            没有可添加的目标。先在「目标」页创建目标，或把它从其他目标集里移出。
          </Text>
        ) : null}
        {candidates.map((goal) => (
          <View key={goal.id} style={styles.candidateRow}>
            <Checkbox
              checked={selectedGoalIds.has(goal.id)}
              onPress={() => toggleGoalSelection(goal.id)}
              label={`${selectedGoalIds.has(goal.id) ? '取消选择' : '选择'}：${goal.title}`}
              disabled={attachBusy}
            />
            <View style={styles.candidateCopy}>
              <Text style={[styles.goalTitle, { color: colors.ink }]}>{goal.title}</Text>
              <Text style={[styles.goalMeta, { color: colors.inkMuted }]}>
                {GOAL_STATUS_LABEL[goal.status]}
                {goal.deadline
                  ? ` · 截止 ${formatShort(goal.deadline.slice(0, 10))}`
                  : ' · 不设截止'}
              </Text>
            </View>
          </View>
        ))}
      </Dialog>

      <Dialog
        visible={archiveOpen}
        title="归档这个目标集？"
        description="归档后目标不再参与新计划生成；已完成任务和执行历史会保留；旧计划版本仍然可读。"
        closable={!setBusy}
        onRequestClose={cancelArchive}
        actions={[
          {
            label: '取消',
            variant: 'text',
            disabled: setBusy,
            onPress: cancelArchive,
          },
          {
            label: setBusy ? '归档中…' : '确认归档',
            variant: 'filled',
            disabled: setBusy,
            onPress: () => void confirmArchive(),
          },
        ]}>
        {detail ? (
          <View
            style={[
              styles.confirmSummary,
              {
                borderColor: colors.outlineVariant,
                backgroundColor: colors.surfaceContainerLow,
              },
            ]}>
            <Text style={[styles.confirmName, { color: colors.ink }]}>{detail.name}</Text>
            <Text style={[styles.confirmMeta, { color: colors.inkMuted }]}>
              {goalSetCountsLabel(detail)}
            </Text>
          </View>
        ) : null}
      </Dialog>
    </View>
  );
}

function GoalSetCard({ set, onPress }: { set: GoalSetRead; onPress: () => void }) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`打开目标集 ${set.name}`}
      onPress={onPress}
      {...handlers}
      style={({ pressed }) => [
        styles.cardPress,
        {
          opacity: pressed ? 0.9 : 1,
          boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      <Surface
        level="level1"
        radius="lg"
        color={hovered ? colors.surfaceContainerLow : undefined}>
        <View style={styles.card}>
          <View style={styles.cardHead}>
            <Text style={[styles.cardTitle, { color: colors.ink }]} numberOfLines={1}>
              {set.name}
            </Text>
            <StatusBadge status={set.status} />
          </View>
          {set.description ? (
            <Text style={[styles.cardDescription, { color: colors.inkMuted }]} numberOfLines={2}>
              {set.description}
            </Text>
          ) : null}
          <View style={styles.cardMeta}>
            <Text style={[styles.metaText, { color: colors.inkMuted }]}>
              {goalSetCountsLabel(set)}
            </Text>
            <Text style={[styles.createdText, { color: colors.inkFaint }]}>
              创建于 {formatCreatedAt(set.created_at)}
            </Text>
          </View>
        </View>
      </Surface>
    </Pressable>
  );
}

function StatusBadge({ status }: { status: GoalSetStatus }) {
  const { colors } = useTheme();
  const active = status === 'active';
  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: active ? colors.secondaryContainer : colors.surfaceContainerHigh,
        },
      ]}>
      <Text
        style={[
          styles.badgeText,
          { color: active ? colors.onSecondaryContainer : colors.inkMuted },
        ]}>
        {goalSetStatusLabel(status)}
      </Text>
    </View>
  );
}

function GoalRow({
  goal,
  busy,
  disabled,
  onToggle,
}: {
  goal: GoalDetailRead;
  busy: boolean;
  disabled: boolean;
  onToggle: () => void;
}) {
  const { colors } = useTheme();
  const tone =
    goal.status === 'archived' || goal.status === 'cancelled'
      ? colors.inkFaint
      : goal.status === 'draft'
        ? colors.warning
        : colors.primary;

  return (
    <Surface level="level0" radius="md" tone="low">
      <View style={styles.goalRow}>
        <View style={styles.goalMain}>
          <Text style={[styles.goalTitle, { color: colors.ink }]} numberOfLines={2}>
            {goal.title}
          </Text>
          <View style={styles.goalMetaRow}>
            <Text style={[styles.goalStatus, { color: tone }]}>
              {GOAL_STATUS_LABEL[goal.status]}
            </Text>
            <Text style={[styles.goalMeta, { color: colors.inkMuted }]}>
              {goal.deadline
                ? `截止 ${formatShort(goal.deadline.slice(0, 10))}`
                : '不设截止'}
            </Text>
          </View>
        </View>
        <Button
          label={busy ? '处理中…' : goal.status === 'archived' ? '恢复' : '归档'}
          variant="outlined"
          size="sm"
          disabled={disabled}
          onPress={onToggle}
        />
      </View>
    </Surface>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    minHeight: 0,
  },
  scroll: {
    flex: 1,
    minHeight: 0,
  },
  scrollContent: {
    gap: Space.xl,
    paddingBottom: Space.xl,
  },
  header: {
    gap: Space.sm,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  headerCopy: {
    flexGrow: 1,
    flexBasis: 320,
    gap: Space.sm,
  },
  title: {
    fontSize: Type.titleLarge,
    fontWeight: '600',
  },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 560,
  },
  filterRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: Space.sm,
  },
  list: {
    gap: Space.md,
  },
  cardPress: {
    borderRadius: Radius.lg,
  },
  card: {
    padding: Space.lg,
    gap: Space.sm,
  },
  cardHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  cardTitle: {
    flex: 1,
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  cardDescription: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.normal,
  },
  cardMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: Space.sm,
  },
  metaText: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
  createdText: {
    fontSize: Type.labelMedium,
  },
  badge: {
    borderRadius: Radius.pill,
    paddingHorizontal: Space.sm,
    paddingVertical: 2,
  },
  badgeText: {
    fontSize: Type.labelSmall,
    fontWeight: '600',
  },
  detailSummary: {
    gap: Space.sm,
  },
  detailHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  detailName: {
    flex: 1,
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  archivedNote: {
    padding: Space.md,
  },
  noteText: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  sectionHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  sectionTitle: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  counter: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
  emptyGoals: {
    padding: Space.lg,
    gap: Space.sm,
  },
  emptyTitle: {
    fontSize: Type.bodyLarge,
    fontWeight: '600',
  },
  goalList: {
    gap: Space.sm,
  },
  goalRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
    padding: Space.md,
  },
  goalMain: {
    flex: 1,
    minWidth: 0,
    gap: 2,
  },
  goalTitle: {
    fontSize: Type.bodyLarge,
    lineHeight: Type.bodyLarge * Line.normal,
    fontWeight: '600',
  },
  goalMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  goalStatus: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  goalMeta: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
  candidateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
  },
  candidateCopy: {
    flex: 1,
    minWidth: 0,
    gap: 2,
  },
  confirmSummary: {
    borderWidth: 1,
    borderRadius: Radius.md,
    padding: Space.md,
    gap: Space.xs,
  },
  confirmName: {
    fontSize: Type.bodyLarge,
    fontWeight: '600',
  },
  confirmMeta: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
});
