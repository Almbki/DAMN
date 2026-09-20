import { useCallback, useMemo, useState } from 'react';
import { StyleSheet, Text, TextInput, View, useWindowDimensions } from 'react-native';

import { BatchBar } from '@/components/batch-bar';
import { CircularChart } from '@/components/circular-chart';
import { NowCard } from '@/components/now-card';
import { SmartListTabs } from '@/components/smart-list-tabs';
import { TaskEditor } from '@/components/task-editor';
import { TaskRow } from '@/components/task-row';
import { Button } from '@/components/ui/button';
import { Segmented } from '@/components/ui/segmented';
import { EmptyState } from '@/components/ui/states';
import { Layout, Line, Radius, Space, Type } from '@/constants/tokens';
import { mockWhyNow } from '@/data/mock';
import { addDays, todayISO } from '@/domain/date';
import { isClosed, type Task } from '@/domain/task';
import { useListKeys } from '@/hooks/use-list-keys';
import { usePlan, type SmartListKey } from '@/state/plan';
import { useTheme } from '@/state/theme';

const VIEWS = ['列表', '概览'];

const BLANK_TASK: Task = {
  id: -1,
  title: '',
  description: '',
  notes: '',
  done: false,
  skipped: false,
  startDate: null,
  startTime: null,
  dueDate: null,
  dueTime: null,
  estimatedMinutes: null,
  actualMinutes: null,
  repeat: { freq: 'none', interval: 1, end: 'never', until: null, count: null },
  tags: [],
  order: -1,
  completedAt: null,
};

export default function TodoScreen() {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const wide = width > 0 && width >= Layout.breakpoint;
  const {
    tasks,
    lists,
    listCounts,
    currentTask,
    ruler,
    energyLabelText,
    stats,
    addTask,
    createTask,
    updateTask,
    deleteTask,
    toggleDone,
    setSkipped,
    reorder,
    moveBy,
    batchSetDone,
    batchDelete,
    batchReschedule,
    logFocus,
  } = usePlan();

  const [draft, setDraft] = useState('');
  const [listKey, setListKey] = useState<SmartListKey>('today');
  const [view, setView] = useState(0);
  const [batchMode, setBatchMode] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null | undefined>(undefined);
  const [draggingId, setDraggingId] = useState<number | null>(null);

  const visible = lists[listKey];
  const editingTask =
    editingId === undefined
      ? null
      : editingId === null
        ? BLANK_TASK
        : (tasks.find((task) => task.id === editingId) ?? null);

  const remainingMinutes = useMemo(
    () =>
      lists.all
        .filter((task) => !isClosed(task))
        .reduce((sum, task) => sum + (task.estimatedMinutes ?? 0), 0),
    [lists.all],
  );

  const selectedSet = useMemo(() => new Set(selected), [selected]);

  function toggleSelect(id: number) {
    setSelected((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  }

  function exitBatch() {
    setBatchMode(false);
    setSelected([]);
  }

  const move = useCallback(
    (delta: number) => {
      if (visible.length === 0) return;
      setActiveId((current) => {
        const fromId = current ?? currentTask?.id ?? visible[0].id;
        const index = visible.findIndex((task) => task.id === fromId);
        const next = Math.min(visible.length - 1, Math.max(0, index + delta));
        return visible[next].id;
      });
    },
    [visible, currentTask],
  );
  const toggleActive = useCallback(() => {
    const id = activeId ?? currentTask?.id ?? visible[0]?.id;
    if (id == null) return;
    setActiveId(id);
    toggleDone(id);
  }, [activeId, currentTask, visible, toggleDone]);
  const skipActive = useCallback(() => {
    const id = activeId ?? currentTask?.id ?? visible[0]?.id;
    if (id == null) return;
    setActiveId(id);
    setSkipped(id, true);
  }, [activeId, currentTask, visible, setSkipped]);
  useListKeys({ onPrev: () => move(-1), onNext: () => move(1), onToggle: toggleActive, onSkip: skipActive });

  function submitQuickAdd() {
    if (!draft.trim()) return;
    addTask(draft, { dueDate: listKey === 'today' ? todayISO() : null });
    setDraft('');
  }

  return (
    <View style={styles.page}>
      <View style={styles.addBlock}>
        <View style={styles.addBar}>
          <TextInput
            value={draft}
            onChangeText={setDraft}
            onSubmitEditing={submitQuickAdd}
            placeholder="输入任务，按回车添加…"
            placeholderTextColor={colors.inkFaint}
            returnKeyType="done"
            accessibilityLabel="快速添加任务"
            testID="quick-add"
            style={[
              styles.input,
              { color: colors.ink, borderColor: colors.line, backgroundColor: colors.paper },
            ]}
          />
          <Button label="添加" variant="primary" onPress={submitQuickAdd} />
          <Button label="详细" variant="secondary" onPress={() => setEditingId(null)} />
        </View>
        <Text style={[styles.quickHint, { color: colors.inkMuted }]}>
          支持快速输入：明天 18:00 交报告
        </Text>
      </View>

      {currentTask ? (
        <NowCard
          key={currentTask.id}
          task={currentTask}
          ruler={ruler}
          energyLabelText={energyLabelText}
          whyText={mockWhyNow}
          onSkip={() => setSkipped(currentTask.id, true)}
          onLogFocus={(minutes) => logFocus(currentTask.id, minutes)}
        />
      ) : (
        <EmptyState
          title="今天没有安排"
          body="在上面写下一个目标，我来把它拆成今天能做完的几步。"
          actionLabel="详细新建"
          onAction={() => setEditingId(null)}
        />
      )}

      <View style={styles.section}>
        <View style={styles.sectionHead}>
          <Text style={[styles.sectionTitle, { color: colors.ink }]}>任务</Text>
          <View style={styles.sectionControls}>
            <View style={styles.viewToggle}>
              <Segmented options={VIEWS} value={view} onChange={setView} />
            </View>
            <Button
              label={batchMode ? '退出多选' : '多选'}
              variant="ghost"
              onPress={() => (batchMode ? exitBatch() : setBatchMode(true))}
            />
          </View>
        </View>

        <SmartListTabs value={listKey} counts={listCounts} onChange={setListKey} />

        {batchMode ? (
          <BatchBar
            count={selected.length}
            onComplete={() => {
              batchSetDone(selected, true);
              exitBatch();
            }}
            onReopen={() => {
              batchSetDone(selected, false);
              exitBatch();
            }}
            onToday={() => {
              batchReschedule(selected, todayISO());
              exitBatch();
            }}
            onTomorrow={() => {
              batchReschedule(selected, addDays(todayISO(), 1));
              exitBatch();
            }}
            onDelete={() => {
              batchDelete(selected);
              exitBatch();
            }}
            onExit={exitBatch}
          />
        ) : null}

        {view === 1 ? (
          <CircularChart tasks={visible} />
        ) : (
          <View style={[styles.list, { borderTopColor: colors.line }]}>
            {visible.length === 0 ? (
              <Text style={[styles.emptyList, { color: colors.inkMuted }]}>这个列表是空的。</Text>
            ) : (
              visible.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  active={task.id === activeId}
                  selected={selectedSet.has(task.id)}
                  batchMode={batchMode}
                  dragging={draggingId === task.id}
                  draggable={wide}
                  onToggleDone={() => toggleDone(task.id)}
                  onOpen={() => setEditingId(task.id)}
                  onToggleSelect={() => toggleSelect(task.id)}
                  onSkip={() => setSkipped(task.id, true)}
                  onDragStart={() => setDraggingId(task.id)}
                  onDragEnter={() => {
                    if (draggingId != null && draggingId !== task.id) {
                      reorder(draggingId, task.id);
                      setDraggingId(task.id);
                    }
                  }}
                  onDragEnd={() => setDraggingId(null)}
                />
              ))
            )}
          </View>
        )}

        {wide && view === 0 ? (
          <Text style={[styles.keys, { color: colors.inkMuted }]}>
            ↑ ↓ 移动 · 空格完成 · L 今天先不做 · 拖动 ≡ 排序
          </Text>
        ) : null}
      </View>

      <Text style={[styles.footnote, { color: colors.inkMuted, maxWidth: wide ? 560 : undefined }]}>
        共 <Text style={styles.mono}>{stats.openCount}</Text> 件未完成 · 剩余{' '}
        <Text style={styles.mono}>{remainingMinutes}</Text> 分钟 · 已完成{' '}
        <Text style={styles.mono}>{stats.completedToday}</Text> 件
      </Text>

      {editingTask ? (
        <TaskEditor
          key={editingId ?? 'new'}
          task={editingTask}
          isNew={editingId === null}
          onClose={() => setEditingId(undefined)}
          onSave={(id, patch) => {
            if (id === -1) {
              createTask({
                title: patch.title ?? '',
                description: patch.description,
                notes: patch.notes,
                startDate: patch.startDate ?? null,
                startTime: patch.startTime ?? null,
                dueDate: patch.dueDate ?? null,
                dueTime: patch.dueTime ?? null,
                estimatedMinutes: patch.estimatedMinutes ?? null,
                repeat: patch.repeat,
              });
            } else {
              updateTask(id, patch);
            }
          }}
          onDelete={deleteTask}
          onMove={moveBy}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    gap: Space.xxl,
  },
  mono: {
    fontFamily: 'IBMPlexMono_500Medium',
  },
  addBlock: {
    gap: Space.sm,
  },
  addBar: {
    flexDirection: 'row',
    gap: Space.sm,
    alignItems: 'stretch',
  },
  input: {
    flex: 1,
    minHeight: 44,
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.md,
    fontSize: Type.body,
  },
  quickHint: {
    fontSize: Type.small,
  },
  section: {
    gap: Space.md,
  },
  sectionHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
    flexWrap: 'wrap',
  },
  sectionTitle: {
    fontSize: Type.title,
    fontWeight: '700',
  },
  sectionControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
    flexWrap: 'wrap',
  },
  viewToggle: {
    minWidth: 160,
  },
  list: {
    borderTopWidth: 1,
  },
  emptyList: {
    fontSize: Type.body,
    paddingVertical: Space.xl,
  },
  keys: {
    fontSize: Type.small,
  },
  footnote: {
    fontSize: Type.small,
    lineHeight: Type.small * Line.relaxed,
  },
});
