import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { DecomposePreviewDialog } from '@/components/decompose-preview-dialog';
import { TaskAddDialog, type PendingTaskInput } from '@/components/task-add-dialog';
import { Button, ExtendedFab, Fab } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import { formatShort } from '@/domain/date';
import type { DraftTask, PendingTask } from '@/domain/decompose';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

export default function GoalScreen() {
  const { colors } = useTheme();
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
  } = usePlan();

  const [addOpen, setAddOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [preview, setPreview] = useState<DraftTask[] | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [previewMessage, setPreviewMessage] = useState<string | null>(null);

  const editingItem = editingId == null ? undefined : pendingTasks.find((item) => item.id === editingId);

  function submit(input: PendingTaskInput) {
    if (editingId != null) updatePendingTask(editingId, input);
    else addPendingTask(input);
    setAddOpen(false);
    setEditingId(null);
  }

  async function startDecompose() {
    setPreviewBusy(true);
    setPreviewMessage(null);
    try {
      const drafts = await decomposePreview();
      setPreview(drafts.length > 0 ? drafts : null);
    } finally {
      setPreviewBusy(false);
    }
  }

  async function regenerate(feedback: string) {
    setPreviewBusy(true);
    try {
      const result = await adjustPreview(feedback);
      setPreviewMessage(result.message);
      if (result.applied) setPreview(null);
      else if (result.drafts) setPreview(result.drafts);
    } finally {
      setPreviewBusy(false);
    }
  }

  async function confirm() {
    setPreviewBusy(true);
    try {
      await confirmPreview();
      setPreview(null);
      setPreviewMessage(null);
    } finally {
      setPreviewBusy(false);
    }
  }

  return (
    <View style={styles.page}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.ink }]}>待拆解</Text>
        <Text style={[styles.body, { color: colors.inkMuted }]}>
          写下想做的事，可以加多条。点「拆解」后，系统会把它们一起理解、拆成每天的任务。
        </Text>
      </View>

      {pendingTasks.length === 0 ? (
        <Surface level="level0" radius="lg" bordered>
          <View style={styles.empty}>
            <Text style={[styles.emptyTitle, { color: colors.ink }]}>还没有要拆解的任务</Text>
            <Text style={[styles.body, { color: colors.inkMuted }]}>
              点右下角的「＋」添加一个任务。加够之后，点「拆解」看系统怎么排。
            </Text>
          </View>
        </Surface>
      ) : (
        <View style={styles.list}>
          {pendingTasks.map((item) => (
            <PendingCard
              key={item.id}
              item={item}
              onEdit={() => {
                setEditingId(item.id);
                setAddOpen(true);
              }}
              onRemove={() => removePendingTask(item.id)}
            />
          ))}
        </View>
      )}

      <View style={styles.fabBar}>
        <Fab
          icon="plus"
          label="添加任务"
          variant="tonal"
          onPress={() => {
            setEditingId(null);
            setAddOpen(true);
          }}
        />
        <ExtendedFab
          icon="target"
          label={
            previewBusy
              ? previewMeta?.stage
                ? `拆解中 · ${previewMeta.stage}`
                : '拆解中…'
              : pendingTasks.length > 0
                ? `拆解 · ${pendingTasks.length}`
                : '拆解'
          }
          disabled={pendingTasks.length === 0 || previewBusy}
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

      {preview ? (
        <DecomposePreviewDialog
          mode={mode}
          tasks={preview}
          canAdjust={previewMeta?.canAdjust ?? true}
          busy={previewBusy}
          message={previewMessage}
          stage={previewMeta?.stage ?? null}
          warnings={previewMeta?.warnings ?? []}
          onRegenerate={regenerate}
          onConfirm={confirm}
          onClose={() => {
            setPreview(null);
            setPreviewMessage(null);
          }}
        />
      ) : null}
    </View>
  );
}

function PendingCard({
  item,
  onEdit,
  onRemove,
}: {
  item: PendingTask;
  onEdit: () => void;
  onRemove: () => void;
}) {
  const { colors } = useTheme();
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
          <Text style={[styles.cardMeta, { color: colors.inkMuted }]}>
            {item.dueDate ? `截止 ${formatShort(item.dueDate)}` : '无截止'}
          </Text>
          <View style={styles.cardActions}>
            <Button label="编辑" variant="text" size="sm" onPress={onEdit} />
            <Button label="删除" variant="text" size="sm" onPress={onRemove} />
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
    gap: Space.xl,
    // Clear the two stacked FABs (56 + 16 + 56) plus their bottom inset.
    paddingBottom: 160,
  },
  header: {
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
  empty: {
    padding: Space.xl,
    gap: Space.sm,
  },
  emptyTitle: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
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
  cardMeta: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
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
