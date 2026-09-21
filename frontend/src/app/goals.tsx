import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Surface } from '@/components/surface';
import { Button } from '@/components/ui/button';
import { TextField } from '@/components/ui/text-field';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import {
  mockAiReplies,
  mockGoalChat,
  mockGoalDraft,
  mockGoals,
  type ChatMessage,
  type Goal,
} from '@/data/mock';
import { useTheme } from '@/state/theme';

type Phase = 'list' | 'draft' | 'chat';
type Step = { title: string; minutes: number };

export default function GoalsScreen() {
  const { colors } = useTheme();

  const [phase, setPhase] = useState<Phase>('list');
  const [goals, setGoals] = useState<Goal[]>(mockGoals);
  const [title, setTitle] = useState(mockGoalDraft.title);
  const [steps, setSteps] = useState<Step[]>(mockGoalDraft.steps);
  const [chat, setChat] = useState<ChatMessage[]>(mockGoalChat);
  const [message, setMessage] = useState('');
  const [cursor, setCursor] = useState(100);

  function startAdd() {
    setTitle(mockGoalDraft.title);
    setSteps(mockGoalDraft.steps.map((step) => ({ ...step })));
    setChat(mockGoalChat);
    setMessage('');
    setPhase('draft');
  }

  /** Leaving the flow early keeps the work: it is stored as a draft. */
  function saveAsDraft() {
    setGoals((prev) => [
      ...prev,
      {
        id: cursor,
        title: title.trim() || '未命名目标',
        progress: 0,
        dueLabel: '未定',
        status: 'draft',
      },
    ]);
    setCursor((value) => value + 1);
    setPhase('list');
  }

  function confirm() {
    setGoals((prev) => [
      {
        id: cursor,
        title: title.trim() || '未命名目标',
        progress: 0,
        dueLabel: '进行中',
        status: 'active',
      },
      ...prev,
    ]);
    setCursor((value) => value + 1);
    setPhase('list');
  }

  function send() {
    const text = message.trim();
    if (!text) return;
    const reply = mockAiReplies[chat.length % mockAiReplies.length];
    setChat((prev) => [
      ...prev,
      { id: cursor, role: 'me', text },
      { id: cursor + 1, role: 'ai', text: reply },
    ]);
    setCursor((value) => value + 2);
    setMessage('');
  }

  function updateStep(index: number, value: string) {
    setSteps((prev) => prev.map((step, i) => (i === index ? { ...step, title: value } : step)));
  }

  return (
    <View style={styles.page}>
      <View style={styles.head}>
        <Text style={[styles.pageTitle, { color: colors.ink }]}>目标</Text>
        {phase === 'list' ? (
          <Button label="添加目标" variant="primary" onPress={startAdd} />
        ) : null}
      </View>

      {phase === 'list' ? <GoalList goals={goals} /> : null}

      {phase === 'draft' ? (
        <View style={styles.flow}>
          <TextField label="目标" value={title} onChangeText={setTitle} />

          <Surface elevation="raised" radius={Radius.lg} style={styles.card}>
            <Text style={[styles.cardTitle, { color: colors.ink }]}>草案预览</Text>
            <Text style={[styles.cardHint, { color: colors.inkMuted }]}>
              这是按目标拆出来的第一步，还可以继续澄清。
            </Text>
            {steps.map((step, index) => (
              <View key={index} style={[styles.stepRow, { borderTopColor: colors.line }]}>
                <Text style={[styles.stepIndex, { color: colors.inkMuted }]}>
                  {String(index + 1).padStart(2, '0')}
                </Text>
                <Text style={[styles.stepTitle, { color: colors.ink }]}>{step.title}</Text>
                <Text style={[styles.stepMinutes, { color: colors.inkMuted }]}>{step.minutes} 分</Text>
              </View>
            ))}
          </Surface>

          <View style={styles.flowActions}>
            <Button label="和 AI 澄清" variant="primary" onPress={() => setPhase('chat')} />
            <Button label="取消，存为草稿" variant="ghost" onPress={saveAsDraft} />
          </View>
        </View>
      ) : null}

      {phase === 'chat' ? (
        <View style={styles.flow}>
          <TextField label="目标" value={title} onChangeText={setTitle} />

          <Surface elevation="raised" radius={Radius.lg} style={styles.card}>
            <Text style={[styles.cardTitle, { color: colors.ink }]}>拆解（可编辑）</Text>
            {steps.map((step, index) => (
              <View key={index} style={styles.editRow}>
                <Text style={[styles.stepIndex, { color: colors.inkMuted }]}>
                  {String(index + 1).padStart(2, '0')}
                </Text>
                <View style={styles.editField}>
                  <TextField
                    label={`第 ${index + 1} 步`}
                    value={step.title}
                    onChangeText={(value) => updateStep(index, value)}
                  />
                </View>
                <Text style={[styles.stepMinutes, { color: colors.inkMuted }]}>{step.minutes} 分</Text>
              </View>
            ))}
          </Surface>

          <Surface elevation="raised" radius={Radius.lg} style={styles.card}>
            <Text style={[styles.cardTitle, { color: colors.ink }]}>和 AI 澄清</Text>
            <View style={styles.chatLog}>
              {chat.map((item) => (
                <Surface
                  key={item.id}
                  elevation="inset"
                  radius={Radius.sm}
                  style={[styles.bubble, item.role === 'me' ? styles.bubbleMe : null]}>
                  <Text style={[styles.bubbleRole, { color: colors.inkMuted }]}>
                    {item.role === 'me' ? '我' : 'AI'}
                  </Text>
                  <Text style={[styles.bubbleText, { color: colors.ink }]}>{item.text}</Text>
                </Surface>
              ))}
            </View>
            <TextField
              label="补充说明"
              value={message}
              onChangeText={setMessage}
              placeholder="例如：这周只能练两次…"
            />
            <View style={styles.sendRow}>
              <Button label="发送" variant="secondary" onPress={send} />
            </View>
          </Surface>

          <View style={styles.flowActions}>
            <Button label="确认创建" variant="primary" onPress={confirm} />
            <Button label="取消，存为草稿" variant="ghost" onPress={saveAsDraft} />
          </View>
        </View>
      ) : null}
    </View>
  );
}

function GoalList({ goals }: { goals: Goal[] }) {
  const { colors } = useTheme();

  if (goals.length === 0) {
    return <Text style={[styles.empty, { color: colors.inkMuted }]}>还没有目标。</Text>;
  }

  return (
    <View style={styles.list}>
      {goals.map((goal) => {
        const percent = Math.round(goal.progress * 100);
        return (
          <Surface key={goal.id} elevation="raised" radius={Radius.lg} style={styles.card}>
            <View style={styles.goalHead}>
              <Text style={[styles.goalTitle, { color: colors.ink }]}>{goal.title}</Text>
              <Text style={[styles.goalPercent, { color: colors.ink }]}>{percent}%</Text>
            </View>
            <View style={[styles.track, { backgroundColor: colors.panel }]}>
              <View
                style={[styles.fill, { width: `${percent}%`, backgroundColor: colors.accent }]}
              />
            </View>
            <View style={styles.goalMeta}>
              <Text style={[styles.metaText, { color: colors.inkMuted }]}>{goal.dueLabel}</Text>
              <Text
                style={[
                  styles.metaText,
                  { color: goal.status === 'draft' ? colors.inkMuted : colors.accent },
                ]}>
                {goal.status === 'draft' ? '草稿' : '进行中'}
              </Text>
            </View>
          </Surface>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    gap: Space.lg,
  },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  pageTitle: {
    fontSize: Type.heading,
    fontWeight: '700',
  },
  list: {
    gap: Space.md,
  },
  flow: {
    gap: Space.lg,
  },
  flowActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  card: {
    padding: Space.lg,
    gap: Space.md,
  },
  cardTitle: {
    fontSize: Type.title,
    fontWeight: '700',
  },
  cardHint: {
    fontSize: Type.small,
    lineHeight: Type.small * Line.relaxed,
  },
  goalHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  goalTitle: {
    flex: 1,
    fontSize: Type.bodyLg,
    fontWeight: '700',
  },
  goalPercent: {
    fontSize: Type.heading,
    fontFamily: Fonts.mono,
  },
  track: {
    height: 8,
    borderRadius: Radius.full,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: Radius.full,
  },
  goalMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  metaText: {
    fontSize: Type.small,
  },
  stepRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
    borderTopWidth: 1,
    paddingTop: Space.sm,
  },
  stepIndex: {
    fontSize: Type.small,
    fontFamily: Fonts.mono,
  },
  stepTitle: {
    flex: 1,
    fontSize: Type.body,
  },
  stepMinutes: {
    fontSize: Type.small,
    fontFamily: Fonts.mono,
  },
  editRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Space.md,
  },
  editField: {
    flex: 1,
  },
  chatLog: {
    gap: Space.sm,
  },
  bubble: {
    padding: Space.md,
    gap: Space.xs,
    maxWidth: '90%',
    alignSelf: 'flex-start',
  },
  bubbleMe: {
    alignSelf: 'flex-end',
  },
  bubbleRole: {
    fontSize: Type.micro,
  },
  bubbleText: {
    fontSize: Type.body,
    lineHeight: Type.body * Line.normal,
  },
  sendRow: {
    flexDirection: 'row',
  },
  empty: {
    fontSize: Type.body,
    paddingVertical: Space.lg,
  },
});
