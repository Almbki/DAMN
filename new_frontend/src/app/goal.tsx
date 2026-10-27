import { useRouter, type Href } from 'expo-router';
import { useState } from 'react';
import {
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ClarificationDialog } from '@/components/clarification-dialog';
import { DecomposePreviewDialog } from '@/components/decompose-preview-dialog';
import { TaskAddDialog, type PendingTaskInput } from '@/components/task-add-dialog';
import { weekdaysSummary } from '@/components/task/weekday-picker';
import { Button, ExtendedFab, Fab } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { EmptyState, InlineNotice } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { Fonts, Layout, Line, Radius, Space, Type } from '@/constants/tokens';
import { formatShort, parseISO } from '@/domain/date';
import type { PendingTask } from '@/domain/decompose';
import { PLANNING_MODE_LABEL, planningModeFromTaskKind } from '@/domain/task';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

export default function GoalScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const wide = width > 0 && width >= Layout.breakpoint;
  const {
    mode,
    pendingTasks,
    addPendingTask,
    updatePendingTask,
    removePendingTask,
    decomposePreview,
    adjustPreview,
    confirmPreview,
    previewMeta,
    previewTasks,
    previewBusy,
    dismissPreview,
    clarification,
    submitClarifications,
    dismissClarification,
    lastConfirmedPlanId,
    clearLastConfirmed,
    actionError,
    clearActionError,
  } = usePlan();

  const [addOpen, setAddOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [previewMessage, setPreviewMessage] = useState<string | null>(null);
  const [previewHidden, setPreviewHidden] = useState(false);
  const editingLocked = previewTasks != null;

  const editingItem = editingId == null ? undefined : pendingTasks.find((item) => item.id === editingId);

  function submit(input: PendingTaskInput) {
    if (editingLocked) return;
    if (editingId != null) updatePendingTask(editingId, input);
    else addPendingTask(input);
    setAddOpen(false);
    setEditingId(null);
  }

  function openAdd() {
    if (editingLocked) return;
    setEditingId(null);
    setAddOpen(true);
  }

  async function startDecompose() {
    if (editingLocked) return;
    clearLastConfirmed();
    setPreviewMessage(null);
    setPreviewHidden(false);
    await decomposePreview();
  }

  async function regenerate(feedback: string) {
    const result = await adjustPreview(feedback);
    setPreviewMessage(result.message);
  }

  async function confirm() {
    setPreviewMessage(null);
    const planId = await confirmPreview();
    if (planId != null) {
      // The preview is consumed by the provider before this resolves. Navigate
      // only on a confirmed plan so a failed request stays retryable.
      setPreviewHidden(false);
      clearLastConfirmed();
      router.replace('/');
    }
  }

  return (
    <View style={styles.page}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <View style={styles.titleRow}>
            <View style={styles.titleLead}>
              <Text style={[styles.title, { color: colors.ink }]}>待拆解</Text>
              {pendingTasks.length > 0 ? (
                <View style={[styles.countPill, { backgroundColor: colors.secondaryContainer }]}>
                  <Text style={[styles.countText, { color: colors.onSecondaryContainer }]}>
                    {pendingTasks.length} 条待处理
                  </Text>
                </View>
              ) : null}
            </View>
            <Button
              label="目标集"
              icon="list"
              variant="tonal"
              size="sm"
              onPress={() => router.push('/goal-sets' as Href)}
            />
          </View>
          <Text style={[styles.body, { color: colors.inkMuted }]}>
            写下想做的事，可以加多条。点「拆解」后，系统会把它们一起理解、拆成每天的任务。
          </Text>
        </View>

        {editingLocked && previewHidden ? (
          <Surface level="level2" radius="lg" bordered style={{ borderColor: colors.primary }}>
            <View style={styles.success}>
              <View style={styles.successHead}>
                <View style={[styles.successIcon, { backgroundColor: colors.primaryContainer }]}>
                  <Icon name="clock" size={18} color={colors.onPrimaryContainer} strokeWidth={2.2} />
                </View>
                <Text style={[styles.successTitle, { color: colors.ink }]}>计划待确认</Text>
              </View>
              <Text style={[styles.body, { color: colors.inkMuted }]}>
                拆解结果还没有确认。继续查看并确认，或放弃这次预览。
              </Text>
              <View style={styles.successActions}>
                <Button
                  label="继续查看计划"
                  variant="filled"
                  icon="arrowRight"
                  onPress={() => setPreviewHidden(false)}
                />
                <Button
                  label="放弃预览"
                  variant="text"
                  onPress={() => {
                    dismissPreview();
                    setPreviewMessage(null);
                    setPreviewHidden(false);
                  }}
                />
              </View>
            </View>
          </Surface>
        ) : null}

        {editingLocked ? (
          <InlineNotice tone="info" message="请先完成当前计划" />
        ) : null}

        {actionError && !previewTasks ? (
          <InlineNotice message={actionError} onDismiss={clearActionError} />
        ) : null}

        {lastConfirmedPlanId != null ? (
          <Surface level="level2" radius="lg" bordered style={{ borderColor: colors.primary }}>
            <View style={styles.success}>
              <View style={styles.successHead}>
                <View style={[styles.successIcon, { backgroundColor: colors.primaryContainer }]}>
                  <Icon name="check" size={18} color={colors.onPrimaryContainer} strokeWidth={2.4} />
                </View>
                <Text style={[styles.successTitle, { color: colors.ink }]}>计划已生成</Text>
              </View>
              <Text style={[styles.body, { color: colors.inkMuted }]}>
                任务已经排进待办。去待办看看每天做什么，还可以逐条调整。
              </Text>
              <View style={styles.successActions}>
                <Button
                  label="去待办"
                  variant="filled"
                  icon="arrowRight"
                  onPress={() => {
                    clearLastConfirmed();
                    router.replace('/');
                  }}
                />
                <Button label="继续添加" variant="text" onPress={clearLastConfirmed} />
              </View>
            </View>
          </Surface>
        ) : pendingTasks.length === 0 ? (
          <EmptyState
            title="还没有要拆解的任务"
            body="先写一件想推进的事，可以一次加多条。加好后点右下角「拆解」，系统会先给一版可以预览、可以反馈的安排。"
            actionLabel={editingLocked ? undefined : '添加第一条'}
            actionIcon="plus"
            onAction={editingLocked ? undefined : openAdd}
          />
        ) : (
          <View style={styles.list}>
            {pendingTasks.map((item) => (
              <PendingCard
                key={item.id}
                item={item}
                disabled={editingLocked}
                onEdit={() => {
                  if (editingLocked) return;
                  setEditingId(item.id);
                  setAddOpen(true);
                }}
                onRemove={() => {
                  if (editingLocked) return;
                  removePendingTask(item.id);
                }}
              />
            ))}
          </View>
        )}
      </ScrollView>

      <View
        style={[
          styles.fabBar,
          { bottom: Space.lg + (wide ? insets.bottom : 0) },
        ]}>
        <Fab
          icon="plus"
          label="添加任务"
          variant="tonal"
          disabled={editingLocked}
          onPress={openAdd}
        />
        <ExtendedFab
          icon="target"
          label={
            previewBusy
              ? previewMeta?.stage
                ? `拆解中 · ${previewMeta.stage}`
                : '拆解中…'
              : editingLocked
                ? '计划待确认'
                : pendingTasks.length > 0
                  ? `拆解 · ${pendingTasks.length} 条`
                  : '拆解'
          }
          disabled={pendingTasks.length === 0 || previewBusy || editingLocked}
          onPress={startDecompose}
        />
      </View>

      {addOpen ? (
        <TaskAddDialog
          key={editingId ?? 'new'}
          initial={editingItem}
          onClose={() => {
            setAddOpen(false);
            setEditingId(null);
          }}
          onSubmit={submit}
        />
      ) : null}

      {clarification ? (
        <ClarificationDialog
          clarification={clarification}
          busy={previewBusy}
          onSubmit={submitClarifications}
          onClose={dismissClarification}
        />
      ) : null}

      {previewTasks && !previewHidden ? (
        <DecomposePreviewDialog
          mode={mode}
          tasks={previewTasks}
          canAdjust={previewMeta?.canAdjust ?? true}
          busy={previewBusy}
          message={previewMessage}
          stage={previewMeta?.stage ?? null}
          warnings={previewMeta?.warnings ?? []}
          violations={previewMeta?.violations ?? []}
          estimatedTotalMinutes={previewMeta?.estimatedTotalMinutes ?? 0}
          dailyLimitMinutes={previewMeta?.dailyLimitMinutes ?? null}
          error={actionError}
          onDismissError={clearActionError}
          onRegenerate={regenerate}
          onConfirm={confirm}
          onDefer={() => setPreviewHidden(true)}
          onClose={() => {
            dismissPreview();
            setPreviewMessage(null);
            setPreviewHidden(false);
          }}
        />
      ) : null}
    </View>
  );
}

function formatCalendarDay(date: string): string {
  const day = parseISO(date);
  return `${day.getMonth() + 1} 月 ${day.getDate()} 日`;
}

function PendingCard({
  item,
  disabled,
  onEdit,
  onRemove,
}: {
  item: PendingTask;
  disabled?: boolean;
  onEdit: () => void;
  onRemove: () => void;
}) {
  const { colors } = useTheme();
  const mode = item.planningMode ?? planningModeFromTaskKind(item.taskKind);
  const isSeries = mode === 'recurring' || mode === 'project_recurring';
  const seriesBits = [
    weekdaysSummary(item.recurrenceWeekdays),
    item.dailyTargetMinutes != null ? `每天 ${item.dailyTargetMinutes} 分钟` : null,
    item.targetAmount != null
      ? `目标 ${item.targetAmount}${item.targetUnit ? ` ${item.targetUnit}` : ''}`
      : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <Surface level="level1" radius="lg">
      <View style={styles.card}>
        <View style={styles.cardHead}>
          <Text style={[styles.cardTitle, { color: colors.ink }]}>{item.title}</Text>
          <PriorityTag priority={item.priority} />
        </View>
        {item.notes ? (
          <Text style={[styles.cardNotes, { color: colors.inkMuted }]} numberOfLines={2}>
            {item.notes}
          </Text>
        ) : null}
        <View style={styles.cardFooter}>
          <View style={styles.cardMetaBlock}>
            <Text style={[styles.cardMeta, { color: colors.inkMuted }]}>
              {`${PLANNING_MODE_LABEL[mode]} · `}
              {item.dueDate
                ? `${isSeries ? '结束' : '截止'} ${formatShort(item.dueDate)}`
                : isSeries
                  ? '不设结束'
                  : '无截止'}
            </Text>
            {isSeries ? (
              <Text style={[styles.cardSeries, { color: colors.inkFaint }]}>
                {item.startDate ? `开始 ${formatCalendarDay(item.startDate)} · ` : ''}
                {seriesBits}
              </Text>
            ) : null}
          </View>
          <View style={styles.cardActions}>
            <Button
              label="编辑"
              variant="text"
              size="sm"
              disabled={disabled}
              onPress={onEdit}
            />
            <Button
              label="删除"
              variant="text"
              size="sm"
              disabled={disabled}
              onPress={onRemove}
            />
          </View>
        </View>
      </View>
    </Surface>
  );
}

function PriorityTag({ priority }: { priority: number }) {
  const { colors } = useTheme();
  const tone = priority >= 3 ? colors.error : priority === 2 ? colors.warning : colors.inkMuted;
  const label = priority >= 3 ? '高' : priority === 2 ? '中' : '低';
  return (
    <View style={styles.priority}>
      <Icon name="flag" size={14} color={tone} strokeWidth={1.6} />
      <Text style={[styles.priorityText, { color: tone }]}>{label}</Text>
    </View>
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
    // Let the last card clear the fixed FAB stack.
    paddingBottom: 180,
  },
  header: {
    gap: Space.sm,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
    flexWrap: 'wrap',
  },
  titleLead: {
    flexDirection: 'row',
    alignItems: 'center',
    flexShrink: 1,
    gap: Space.md,
    flexWrap: 'wrap',
  },
  title: {
    fontSize: Type.titleLarge,
    fontWeight: '600',
  },
  countPill: {
    borderRadius: Radius.pill,
    paddingHorizontal: Space.md,
    paddingVertical: Space.xs,
  },
  countText: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 560,
  },
  success: {
    padding: Space.xl,
    gap: Space.md,
  },
  successHead: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
  },
  successIcon: {
    width: 36,
    height: 36,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  successTitle: {
    fontSize: Type.headlineSmall,
    fontWeight: '600',
  },
  successActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: Space.sm,
    paddingTop: Space.xs,
  },
  list: {
    gap: Space.md,
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
  priority: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  priorityText: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  cardNotes: {
    fontSize: Type.bodyMedium,
    lineHeight: Line.normal * Type.bodyMedium,
  },
  cardFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  cardMetaBlock: {
    flexShrink: 1,
    minWidth: 0,
    gap: 2,
  },
  cardMeta: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
  cardSeries: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.normal,
  },
  cardActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
  },
  fabBar: {
    position: 'absolute',
    right: 0,
    bottom: Space.lg,
    alignItems: 'flex-end',
    gap: Space.md,
    // The bar is a fixed rectangle over the page; without `box-none` the empty
    // gap around the buttons swallows taps meant for the card underneath.
    pointerEvents: 'box-none',
  },
});
