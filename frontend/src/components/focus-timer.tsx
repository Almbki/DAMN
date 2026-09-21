import { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import { Surface } from '@/components/surface';
import { Button } from '@/components/ui/button';
import { Segmented } from '@/components/ui/segmented';
import { Fonts, Radius, Space, Type } from '@/constants/tokens';
import type { Task } from '@/domain/task';
import { useTheme } from '@/state/theme';

const MODES = ['正计时', '倒计时'] as const;

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

function formatClock(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  return `${pad(Math.floor(safe / 60))}:${pad(safe % 60)}`;
}

function toInt(value: string, fallback: number): number {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function digits(value: string): string {
  return value.replace(/[^0-9]/g, '').slice(0, 3);
}

type CountdownState = { phase: 'work' | 'rest'; round: number; remaining: number };

/**
 * The inline focus timer. Count up, or a work/rest/rounds countdown config
 * driven by a plain `setInterval` — nothing is persisted in the background.
 */
export function FocusTimer({ task, onLog }: { task: Task; onLog: (minutes: number) => void }) {
  const { colors } = useTheme();

  const [mode, setMode] = useState(0);
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const [work, setWork] = useState(String(task.estimatedMinutes ?? 25));
  const [rest, setRest] = useState('5');
  const [rounds, setRounds] = useState('2');

  const workMinutes = Math.max(1, toInt(work, 25));
  const restMinutes = Math.max(0, toInt(rest, 5));
  const totalRounds = Math.max(1, toInt(rounds, 2));

  const [cd, setCd] = useState<CountdownState>(() => ({
    phase: 'work',
    round: 1,
    remaining: workMinutes * 60,
  }));
  const cdRef = useRef(cd);

  useEffect(() => {
    cdRef.current = cd;
  }, [cd]);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      if (mode === 0) {
        setElapsed((value) => value + 1);
        return;
      }
      const current = cdRef.current;
      if (current.remaining > 1) {
        const next = { ...current, remaining: current.remaining - 1 };
        cdRef.current = next;
        setCd(next);
        return;
      }
      if (current.phase === 'work') {
        if (current.round < totalRounds) {
          const next: CountdownState =
            restMinutes > 0
              ? { phase: 'rest', round: current.round, remaining: restMinutes * 60 }
              : { phase: 'work', round: current.round + 1, remaining: workMinutes * 60 };
          cdRef.current = next;
          setCd(next);
          return;
        }
        onLog(workMinutes * totalRounds);
        setRunning(false);
        const reset: CountdownState = { phase: 'work', round: 1, remaining: workMinutes * 60 };
        cdRef.current = reset;
        setCd(reset);
        return;
      }
      const next: CountdownState = {
        phase: 'work',
        round: current.round + 1,
        remaining: workMinutes * 60,
      };
      cdRef.current = next;
      setCd(next);
    }, 1000);
    return () => clearInterval(id);
  }, [running, mode, totalRounds, workMinutes, restMinutes, onLog]);

  function resetCountdown() {
    setCd({ phase: 'work', round: 1, remaining: workMinutes * 60 });
  }

  function chooseMode(index: number) {
    setMode(index);
    setRunning(false);
    setElapsed(0);
    resetCountdown();
  }

  function changeConfig(setter: (value: string) => void) {
    return (value: string) => {
      setter(digits(value));
      setRunning(false);
      setElapsed(0);
      resetCountdown();
    };
  }

  const clock = mode === 0 ? formatClock(elapsed) : formatClock(cd.remaining);
  const countdownStarted =
    cd.remaining !== workMinutes * 60 || cd.round > 1 || cd.phase !== 'work';
  const started = mode === 0 ? elapsed > 0 : countdownStarted;
  const phaseLabel =
    mode === 0
      ? running
        ? '专注中'
        : elapsed > 0
          ? '已暂停'
          : '还没开始'
      : `${cd.round}/${totalRounds} 轮 · ${cd.phase === 'work' ? '工作' : '休息'}`;
  const elapsedMinutes = Math.max(1, Math.round(elapsed / 60));

  return (
    <Surface elevation="inset" radius={Radius.md} style={styles.panel}>
      <Segmented options={MODES} value={mode} onChange={chooseMode} />

      <View style={styles.clockRow}>
        <Text style={[styles.clock, { color: colors.ink }]}>{clock}</Text>
        <Text style={[styles.phase, { color: colors.inkMuted }]}>{phaseLabel}</Text>
      </View>

      {mode === 1 ? (
        <View style={styles.configRow}>
          <NumField label="工作" value={work} onChangeText={changeConfig(setWork)} />
          <NumField label="休息" value={rest} onChangeText={changeConfig(setRest)} />
          <NumField label="轮次" value={rounds} onChangeText={changeConfig(setRounds)} />
        </View>
      ) : null}

      <View style={styles.actions}>
        <Button
          label={running ? '暂停' : started ? '继续' : '开始'}
          variant="primary"
          onPress={() => setRunning((value) => !value)}
        />
        {mode === 0 && elapsed > 0 ? (
          <Button
            label={`记入 ${elapsedMinutes} 分钟`}
            variant="secondary"
            onPress={() => {
              setRunning(false);
              onLog(elapsedMinutes);
              setElapsed(0);
            }}
          />
        ) : null}
        <Button
          label="重置"
          variant="ghost"
          onPress={() => {
            setRunning(false);
            setElapsed(0);
            resetCountdown();
          }}
        />
      </View>
    </Surface>
  );
}

function NumField({
  label,
  value,
  onChangeText,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
}) {
  const { colors } = useTheme();
  const [focused, setFocused] = useState(false);

  return (
    <View style={styles.field}>
      <Text style={[styles.fieldLabel, { color: colors.inkMuted }]}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        keyboardType="number-pad"
        accessibilityLabel={label}
        style={[
          styles.fieldInput,
          {
            color: colors.ink,
            borderColor: focused ? colors.accent : colors.line,
            backgroundColor: colors.paper,
          },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    padding: Space.lg,
    gap: Space.md,
  },
  clockRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Space.md,
  },
  clock: {
    fontSize: Type.displaySm,
    lineHeight: Type.displaySm,
    fontFamily: Fonts.mono,
  },
  phase: {
    fontSize: Type.small,
    paddingBottom: Space.sm,
  },
  configRow: {
    flexDirection: 'row',
    gap: Space.sm,
  },
  field: {
    flex: 1,
    gap: Space.xs,
  },
  fieldLabel: {
    fontSize: Type.small,
  },
  fieldInput: {
    minHeight: 44,
    borderWidth: 2,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.md,
    fontSize: Type.body,
    fontFamily: Fonts.mono,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
});
