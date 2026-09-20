import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { describeApiError } from '@/api/client';
import { todayString } from '@/api/format';
import type { CognitiveLoad } from '@/api/types';
import { Btn, Card, Checkbox, MonoInput, MonoText, Screen, Tag } from '@/components/mono';
import { MonoSpace } from '@/constants/mono';
import { useMono } from '@/hooks/use-mono';
import { usePlan } from '@/plan/plan-provider';
import { displayMinutes, pickCurrentTask, progress, tasksForDate } from '@/plan/selectors';

/**
 * Todo —— 默认页，也是产品的核心。
 *
 * ## 顶部「添加」其实是**生成计划**
 *
 * 后端没有「单条加任务」的接口，用户能给的输入是**目标**，由 `POST /plans/generate`
 * 同步跑完拆成任务（实测约 1.5s）。所以模板里的添加栏在这里用于输入目标 → 生成计划，
 * 按钮文案改成「生成」，不假装能手动加任务。
 *
 * ## 列表是今天的执行清单
 *
 * 只显示 `scheduled_date === 今天` 的任务；后端默认排期是「今天起 14 天」，
 * 全铺出来会让「今天做这些」失真。勾选是乐观更新，失败回滚并显示后端原因。
 */

/** 认知负荷的短标签（列表里的 tag，不用长句）。 */
const LOAD_TAG: Record<CognitiveLoad, string> = {
  high: '费脑',
  medium: '动脑',
  low: '轻松',
  restorative: '休息',
};

export default function TodoScreen() {
  const c = useMono();
  const { plan, loadState, error: loadError, generate, setTaskCompleted, replan } = usePlan();

  const [goal, setGoal] = useState('');
  const [busy, setBusy] = useState(false);
  const [replanning, setReplanning] = useState(false);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const today = todayString();
  const tasks = tasksForDate(plan, today);
  const current = pickCurrentTask(plan, today);
  const { done, total } = progress(plan);

  const addGoal = async () => {
    const text = goal.trim();
    if (!text || busy) return;
    setBusy(true);
    setActionError(null);
    try {
      await generate(text);
      setGoal('');
    } catch (cause) {
      setActionError(describeApiError(cause));
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (taskId: number, completed: boolean) => {
    setPendingId(taskId);
    setActionError(null);
    try {
      await setTaskCompleted(taskId, completed);
    } catch (cause) {
      setActionError(describeApiError(cause));
    } finally {
      setPendingId(null);
    }
  };

  const pushToTomorrow = async () => {
    setReplanning(true);
    setActionError(null);
    try {
      await replan('把今天没做完的往后挪');
    } catch (cause) {
      setActionError(describeApiError(cause));
    } finally {
      setReplanning(false);
    }
  };

  const loading = loadState === 'loading' || loadState === 'idle';

  return (
    <Screen>
      {/* 添加栏：输入目标 → 生成计划 */}
      <View style={styles.addBar}>
        <MonoInput
          value={goal}
          onChangeText={setGoal}
          onSubmitEditing={() => void addGoal()}
          returnKeyType="done"
          editable={!busy}
          placeholder="写下一个目标，回车生成计划…"
          accessibilityLabel="目标"
          style={styles.addInput}
        />
        <Btn
          label={busy ? '生成中…' : '生成'}
          variant="primary"
          onPress={() => void addGoal()}
          disabled={busy || goal.trim().length === 0}
        />
      </View>

      {plan ? (
        <MonoText type="caption" color="faint">
          v{plan.version} · 今天 {tasks.length} 件 · 全部 {done}/{total} 件
        </MonoText>
      ) : null}

      {loading ? (
        <Card>
          <MonoText type="body" color="faint">
            正在向后端要计划…
          </MonoText>
        </Card>
      ) : loadState === 'error' ? (
        <Card>
          <MonoText type="body" color="danger">
            {loadError}
          </MonoText>
        </Card>
      ) : !plan ? (
        <Card title="还没有计划">
          <MonoText type="body" color="sub">
            在上面写一句想达成的事，后端会把它拆成今天就能动手的任务。
          </MonoText>
        </Card>
      ) : tasks.length === 0 ? (
        <Card title="今天没有排任务">
          <MonoText type="body" color="sub">
            这一天是空的。可以什么都不做，也可以在上面写个新目标再生成一份。
          </MonoText>
        </Card>
      ) : (
        <View style={styles.list}>
          {tasks.map((task) => {
            const isDone = task.status === 'completed';
            const showBusy = pendingId === task.id;
            const isCurrent = current?.id === task.id && !isDone;
            const standards = task.standards ?? [];
            const standardsDone = standards.filter((item) => item.completed).length;

            const meta: string[] = [];
            if (standards.length > 1) meta.push(`子步骤 ${standardsDone}/${standards.length}`);
            if (task.start_time) meta.push(`${task.start_time.slice(0, 5)} 开始`);
            meta.push(`${displayMinutes(task)} 分钟`);

            return (
              <Pressable
                key={task.id}
                onPress={() => void toggle(task.id, !isDone)}
                disabled={showBusy}
                accessibilityRole="checkbox"
                accessibilityState={{ checked: isDone, disabled: showBusy }}
                accessibilityLabel={task.title}
                style={({ pressed }) => [
                  styles.todoItem,
                  {
                    borderColor: isCurrent ? c.strong : c.border,
                    opacity: showBusy ? 0.5 : 1,
                  },
                  pressed && { backgroundColor: c.hover },
                ]}>
                <View style={styles.checkHit}>
                  <Checkbox checked={isDone} disabled={showBusy} />
                </View>

                <View style={styles.todoContent}>
                  <MonoText
                    type="bodyStrong"
                    color={isDone ? 'faint' : 'text'}
                    style={isDone ? styles.doneText : undefined}>
                    {task.title}
                  </MonoText>
                  <MonoText type="caption" color="faint">
                    {meta.join(' · ')}
                  </MonoText>
                  <View style={styles.tagRow}>
                    {isCurrent ? <Tag label="现在" tone="strong" /> : null}
                    <Tag label={LOAD_TAG[task.cognitive_load]} />
                  </View>
                </View>
              </Pressable>
            );
          })}
        </View>
      )}

      {actionError ? (
        <MonoText type="caption" color="danger">
          {actionError}
        </MonoText>
      ) : null}

      {plan && tasks.length > 0 ? (
        <View>
          <Btn
            label={replanning ? '正在重排…' : '今天先做这些，剩下的明天再说'}
            onPress={() => void pushToTomorrow()}
            disabled={replanning}
          />
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  addBar: {
    flexDirection: 'row',
    alignItems: 'stretch',
    gap: MonoSpace.two,
  },
  addInput: { flex: 1, minHeight: 44 },
  list: { gap: MonoSpace.two },
  todoItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: MonoSpace.three,
    padding: MonoSpace.four,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 4,
  },
  checkHit: { paddingTop: 1 },
  todoContent: { flex: 1, gap: MonoSpace.one },
  tagRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: MonoSpace.two,
  },
  doneText: { textDecorationLine: 'line-through' },
});
