import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { describeApiError } from '@/api/client';
import * as endpoints from '@/api/endpoints';
import { todayString } from '@/api/format';
import { Btn, Card, Field, LevelPicker, MonoInput, MonoText, Screen } from '@/components/mono';
import { MonoSpace } from '@/constants/mono';
import { usePlan } from '@/plan/plan-provider';
import { isTaskClosed, tasksForDate } from '@/plan/selectors';
import { useAuthToken } from '@/session/session-provider';

/**
 * 反馈。
 *
 * ## 三个文本框对应后端字段
 *
 * - 「今天完成得怎么样」→ `free_text`
 * - 「没做完的原因」→ `delay_reason`
 * - 「明天想怎么调整」→ 追加进 `free_text`（后端没有单独的调整建议字段，不假装有）
 *
 * ## `completion_rate` 必须按今天的真实完成度算
 *
 * 后端在 `completion_rate < 0.5` 时**会自动重排**。如果偷懒不传，等于告诉后端
 * 「今天一件没做」，用户只是来填个状态，计划却被悄悄重排了 —— 这是这页最危险的地方。
 * 所以完成度永远由今天的任务现算，不让用户手填。
 *
 * 自动重排会产生**新的计划版本**（`replan_plan_id`），必须切过去，
 * 否则界面还在展示已被替代的旧版本。
 */

/** 四档 → 后端 0..10。低档不取 0：用户表达的只是「很低」。 */
const ENERGY_SCALE = [2, 4, 7, 9] as const;
const STRESS_SCALE = [1, 4, 7, 9] as const;

export default function FeedbackScreen() {
  const token = useAuthToken();
  const { plan, switchToPlan } = usePlan();

  const [summary, setSummary] = useState('');
  const [reason, setReason] = useState('');
  const [suggestion, setSuggestion] = useState('');
  const [energy, setEnergy] = useState<number | null>(null);
  const [stress, setStress] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: 'ok' | 'error'; text: string } | null>(null);

  const today = todayString();
  const todayTasks = tasksForDate(plan, today);
  const completedToday = todayTasks.filter((task) => task.status === 'completed').length;
  const completionRate = todayTasks.length === 0 ? 0 : completedToday / todayTasks.length;
  const remainingToday = todayTasks.filter((task) => !isTaskClosed(task)).length;

  const canSubmit = plan !== null && todayTasks.length > 0 && !busy;

  const submit = async () => {
    if (!plan) return;
    setBusy(true);
    setMessage(null);

    try {
      const notes: string[] = [];
      if (summary.trim()) notes.push(summary.trim());
      if (suggestion.trim()) notes.push(`调整建议：${suggestion.trim()}`);

      const result = await endpoints.submitFeedback(token, plan.id, {
        date: today,
        completion_rate: completionRate,
        energy_level: energy === null ? null : ENERGY_SCALE[energy],
        stress_level: stress === null ? null : STRESS_SCALE[stress],
        delay_reason: reason.trim() || null,
        free_text: notes.length > 0 ? notes.join('；') : null,
      });

      if (result.replan_triggered) {
        const next =
          result.replan_plan_id === null || result.replan_plan_id === undefined
            ? null
            : await switchToPlan(result.replan_plan_id);

        setMessage({
          tone: 'ok',
          text: `记下了：完成 ${completedToday}/${todayTasks.length}。后端把剩下的重排了一遍${
            next ? `，现在是 v${next.version}（${next.tasks.length} 件待做）` : ''
          }。`,
        });
      } else {
        setMessage({
          tone: 'ok',
          text: `记下了：完成 ${completedToday}/${todayTasks.length}${
            energy === null ? '' : `，精力 ${ENERGY_SCALE[energy]}/10`
          }${stress === null ? '' : `，压力 ${STRESS_SCALE[stress]}/10`}。`,
        });
      }
    } catch (cause) {
      setMessage({ tone: 'error', text: describeApiError(cause) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <Card title="每日反馈">
        {plan === null ? (
          <MonoText type="body" color="sub">
            还没有计划，这条反馈无处可落。先去 Todo 生成一份计划。
          </MonoText>
        ) : todayTasks.length === 0 ? (
          <MonoText type="body" color="sub">
            今天没有排任务，没有完成度可以报，所以这次不提交反馈（乱报会触发一次没必要的重排）。
          </MonoText>
        ) : (
          <MonoText type="caption" color="faint">
            提交时会带上今天的真实完成度：{completedToday}/{todayTasks.length} 件
            {remainingToday > 0 ? `，还剩 ${remainingToday} 件没做` : ''}
            。完成度低于一半时，后端会自动重排剩下的任务。
          </MonoText>
        )}

        <Field label="今天完成得怎么样">
          <MonoInput
            value={summary}
            onChangeText={setSummary}
            multiline
            textAlignVertical="top"
            placeholder="简述今天完成了哪些任务…"
            accessibilityLabel="今日完成情况"
            style={styles.textarea}
          />
        </Field>

        <Field label="没做完的原因（如有）">
          <MonoInput
            value={reason}
            onChangeText={setReason}
            multiline
            textAlignVertical="top"
            placeholder="例如：被打断、预估时间不足…"
            accessibilityLabel="未完成原因"
            style={styles.textarea}
          />
        </Field>

        <Field label="明天想怎么调整（可选）">
          <MonoInput
            value={suggestion}
            onChangeText={setSuggestion}
            multiline
            textAlignVertical="top"
            placeholder="例如：减少任务量、调整优先级…"
            accessibilityLabel="明日计划调整建议"
            style={styles.textarea}
          />
        </Field>

        <View style={styles.levels}>
          <LevelPicker
            ask="现在有多少精力？"
            options={['很低', '偏低', '还行', '充沛']}
            value={energy}
            onChange={setEnergy}
          />
          <LevelPicker
            ask="压力感大吗？"
            options={['轻松', '尚可', '偏紧', '很紧']}
            value={stress}
            onChange={setStress}
          />
        </View>

        {message ? (
          <MonoText type="caption" color={message.tone === 'error' ? 'danger' : 'sub'}>
            {message.text}
          </MonoText>
        ) : null}

        <Btn
          label={busy ? '正在提交…' : '提交反馈'}
          variant="primary"
          onPress={() => void submit()}
          disabled={!canSubmit}
          full
        />
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  textarea: {
    minHeight: 96,
    paddingTop: MonoSpace.three,
    paddingBottom: MonoSpace.three,
  },
  levels: { gap: MonoSpace.five },
});
