import { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Ruler, type RulerSegment } from '@/components/ruler';
import { Button } from '@/components/ui/button';
import { WhyNote } from '@/components/why-note';
import { Line, Radius, Space, Type } from '@/constants/tokens';
import type { Task } from '@/domain/task';
import { useTheme } from '@/state/theme';

const PRESETS = [25, 45, 5];

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

function formatClock(totalSeconds: number): string {
  return `${pad(Math.floor(totalSeconds / 60))}:${pad(totalSeconds % 60)}`;
}

/**
 * The "now" card, with the focus timer merged in.
 *
 * One hero number: idle it is the task's estimated duration ("25 分钟"); once the
 * timer starts it becomes the countdown ("24:59"). That keeps the single most
 * characteristic thing on screen without stacking two time displays.
 */
export function NowCard({
  task,
  ruler,
  energyLabelText,
  whyText,
  onSkip,
  onLogFocus,
}: {
  task: Task;
  ruler: RulerSegment[];
  energyLabelText: string;
  whyText: string;
  onSkip: () => void;
  onLogFocus: (minutes: number) => void;
}) {
  const { colors } = useTheme();
  const initialPreset = task.estimatedMinutes && PRESETS.includes(task.estimatedMinutes)
    ? task.estimatedMinutes
    : 25;
  const [preset, setPreset] = useState(initialPreset);
  const [remaining, setRemaining] = useState(initialPreset * 60);
  const [running, setRunning] = useState(false);
  const remainingRef = useRef(remaining);

  useEffect(() => {
    remainingRef.current = remaining;
  }, [remaining]);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      const next = Math.max(0, remainingRef.current - 1);
      remainingRef.current = next;
      setRemaining(next);
      if (next === 0) {
        setRunning(false);
        onLogFocus(preset);
        setRemaining(preset * 60);
        remainingRef.current = preset * 60;
      }
    }, 1000);
    return () => clearInterval(id);
  }, [running, preset, onLogFocus]);

  const total = preset * 60;
  const started = remaining !== total;
  const progress = total === 0 ? 0 : 1 - remaining / total;
  const elapsedMinutes = Math.max(1, Math.round((total - remaining) / 60));

  function choosePreset(minutes: number) {
    setPreset(minutes);
    setRemaining(minutes * 60);
    remainingRef.current = minutes * 60;
    setRunning(false);
  }

  function reset() {
    setRemaining(preset * 60);
    remainingRef.current = preset * 60;
    setRunning(false);
  }

  return (
    <View style={[styles.card, { borderColor: colors.lineStrong, backgroundColor: colors.paper }]}>
      <View style={styles.head}>
        <View style={styles.nowTag}>
          <View style={[styles.nowDot, { backgroundColor: colors.mint }]} />
          <Text style={[styles.nowText, { color: colors.ink }]}>现在</Text>
        </View>
        <Text style={[styles.cardTime, { color: colors.inkMuted }]}>
          {task.dueTime ? `${task.dueTime} 前` : '今天'}
        </Text>
      </View>

      {started ? (
        <View style={styles.displayRow}>
          <Text style={[styles.clock, { color: colors.ink }]}>{formatClock(remaining)}</Text>
          <Text style={[styles.clockNote, { color: colors.inkMuted }]}>
            {running ? '专注中' : '已暂停'}
          </Text>
        </View>
      ) : (
        <View style={styles.displayRow}>
          <Text style={[styles.display, { color: colors.ink }]}>{task.estimatedMinutes ?? '—'}</Text>
          <Text style={[styles.unit, { color: colors.inkMuted }]}>分钟</Text>
        </View>
      )}

      <Text style={[styles.taskTitle, { color: colors.ink }]}>{task.title}</Text>
      <Text style={[styles.taskMeta, { color: colors.inkMuted }]}>{energyLabelText}</Text>

      <Ruler segments={ruler} />

      {started ? (
        <View style={[styles.track, { backgroundColor: colors.line }]}>
          <View
            style={[styles.fill, { backgroundColor: colors.mint, width: `${Math.min(100, progress * 100)}%` }]}
          />
        </View>
      ) : null}

      <WhyNote text={whyText} />

      <View style={styles.presets}>
        {PRESETS.map((minutes) => {
          const selected = minutes === preset;
          return (
            <Pressable
              key={minutes}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              onPress={() => choosePreset(minutes)}
              style={[
                styles.preset,
                {
                  borderColor: selected ? colors.ink : colors.line,
                  backgroundColor: selected ? colors.ink : 'transparent',
                },
              ]}>
              <Text style={[styles.presetText, { color: selected ? colors.onInk : colors.ink }]}>
                {minutes} 分钟
              </Text>
            </Pressable>
          );
        })}
      </View>

      <View style={styles.actions}>
        <Button
          label={running ? '暂停' : started ? '继续' : '开始'}
          variant="primary"
          onPress={() => setRunning((value) => !value)}
        />
        {started ? <Button label="重置" variant="ghost" onPress={reset} /> : null}
        {started ? (
          <Button
            label={`记入 ${elapsedMinutes} 分钟`}
            variant="secondary"
            onPress={() => {
              setRunning(false);
              onLogFocus(elapsedMinutes);
              reset();
            }}
          />
        ) : null}
        <Button label="今天先不做" variant="ghost" onPress={onSkip} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: Radius.md,
    padding: Space.xl,
    gap: Space.lg,
  },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  nowTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  nowDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  nowText: {
    fontSize: Type.small,
    fontWeight: '700',
    letterSpacing: 1,
  },
  cardTime: {
    fontSize: Type.small,
    fontFamily: 'IBMPlexMono_400Regular',
  },
  displayRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Space.sm,
  },
  display: {
    fontSize: Type.display,
    lineHeight: Type.display * 0.95,
    fontFamily: 'IBMPlexMono_500Medium',
  },
  clock: {
    fontSize: Type.display,
    lineHeight: Type.display * 0.95,
    fontFamily: 'IBMPlexMono_500Medium',
  },
  clockNote: {
    fontSize: Type.body,
    paddingBottom: 12,
  },
  unit: {
    fontSize: Type.unit,
    lineHeight: Type.unit * 1.2,
    paddingBottom: 10,
  },
  taskTitle: {
    fontSize: Type.heading,
    fontWeight: '700',
    lineHeight: Type.heading * Line.tight,
  },
  taskMeta: {
    fontSize: Type.body,
    lineHeight: Type.body * Line.normal,
  },
  track: {
    height: 10,
    borderRadius: Radius.sm,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: Radius.sm,
  },
  presets: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  preset: {
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.lg,
    minHeight: 36,
    justifyContent: 'center',
  },
  presetText: {
    fontSize: Type.small,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
    flexWrap: 'wrap',
  },
});
