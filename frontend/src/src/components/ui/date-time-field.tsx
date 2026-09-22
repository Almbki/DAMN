import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Radius, Space, Type } from '@/constants/tokens';
import { addDays, formatShort, parseISO, toISO, todayISO } from '@/domain/date';
import { useTheme } from '@/state/theme';

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

/** Build month rows of `YYYY-MM-DD` | null. Explicit rows — no flexWrap. */
function buildWeeks(year: number, month: number): (string | null)[][] {
  const firstDow = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (string | null)[] = [];
  for (let i = 0; i < firstDow; i += 1) cells.push(null);
  for (let day = 1; day <= daysInMonth; day += 1) cells.push(toISO(new Date(year, month, day)));
  while (cells.length % 7 !== 0) cells.push(null);
  const weeks: (string | null)[][] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  return weeks;
}

/**
 * Calendar + time picker built from plain views. No native picker dependency,
 * so it behaves identically on web and Android.
 */
export function DateTimeField({
  label,
  date,
  time,
  onChangeDate,
  onChangeTime,
  withTime = true,
}: {
  label: string;
  date: string;
  time: string;
  onChangeDate: (date: string | null) => void;
  onChangeTime: (time: string | null) => void;
  withTime?: boolean;
}) {
  const { colors } = useTheme();
  const [open, setOpen] = useState(false);
  const [cursor, setCursor] = useState(date || todayISO());
  const [cursorTime, setCursorTime] = useState(time || '09:00');

  const cursorDate = parseISO(cursor);
  const year = cursorDate.getFullYear();
  const month = cursorDate.getMonth();
  const weeks = buildWeeks(year, month);
  const today = todayISO();
  const summary = date ? `${formatShort(date)}${time ? ` ${time}` : ''}` : '未设置';

  function shiftMonth(delta: number) {
    setCursor(toISO(new Date(year, month + delta, 1)));
  }

  function pickDay(value: string) {
    setCursor(value);
    onChangeDate(value);
  }

  function shiftTime(hours: number, minutes: number) {
    const [h, m] = cursorTime.split(':').map(Number);
    let total = h * 60 + m + hours * 60 + minutes;
    total = ((total % 1440) + 1440) % 1440;
    const next = `${pad(Math.floor(total / 60))}:${pad(total % 60)}`;
    setCursorTime(next);
    onChangeTime(next);
  }

  return (
    <View style={styles.wrap}>
      <Text style={[styles.label, { color: colors.inkMuted }]}>{label}</Text>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${label}：${summary}`}
        onPress={() => setOpen((value) => !value)}
        style={[styles.summary, { borderColor: open ? colors.lineStrong : colors.line, backgroundColor: colors.paper }]}>
        <Text
          style={[styles.summaryText, { color: date ? colors.ink : colors.inkFaint }]}
          numberOfLines={1}>
          {summary}
        </Text>
        <Text style={[styles.caret, { color: colors.inkMuted }]}>{open ? '收起' : '选择'}</Text>
      </Pressable>

      {open ? (
        <View style={[styles.panel, { borderColor: colors.line }]}>
          <View style={styles.quickRow}>
            <Quick label="今天" onPress={() => pickDay(today)} />
            <Quick label="明天" onPress={() => pickDay(addDays(today, 1))} />
            <Quick label="后天" onPress={() => pickDay(addDays(today, 2))} />
            <Quick
              label="清除"
              onPress={() => {
                onChangeDate(null);
                onChangeTime(null);
              }}
            />
          </View>

          <View style={styles.monthHead}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="上个月"
              onPress={() => shiftMonth(-1)}
              style={[styles.monthBtn, { borderColor: colors.line }]}>
              <Text style={[styles.monthBtnText, { color: colors.ink }]}>‹</Text>
            </Pressable>
            <Text style={[styles.monthLabel, { color: colors.ink }]}>
              {year} 年 {month + 1} 月
            </Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="下个月"
              onPress={() => shiftMonth(1)}
              style={[styles.monthBtn, { borderColor: colors.line }]}>
              <Text style={[styles.monthBtnText, { color: colors.ink }]}>›</Text>
            </Pressable>
          </View>

          <View style={styles.weekHeader}>
            {WEEKDAYS.map((day) => (
              <Text key={day} style={[styles.weekday, { color: colors.inkMuted }]}>
                {day}
              </Text>
            ))}
          </View>

          {weeks.map((week, weekIndex) => (
            <View key={`w-${weekIndex}`} style={styles.weekRow}>
              {week.map((cell, cellIndex) => {
                if (!cell) return <View key={`e-${weekIndex}-${cellIndex}`} style={styles.dayEmpty} />;
                const selected = cell === date;
                const isToday = cell === today;
                return (
                  <Pressable
                    key={cell}
                    accessibilityRole="button"
                    accessibilityLabel={cell}
                    accessibilityState={{ selected }}
                    onPress={() => pickDay(cell)}
                    style={[
                      styles.dayCell,
                      {
                        borderColor: selected ? colors.ink : isToday ? colors.inkMuted : 'transparent',
                        backgroundColor: selected ? colors.ink : 'transparent',
                      },
                    ]}>
                    <Text style={[styles.dayText, { color: selected ? colors.onInk : colors.ink }]}>
                      {Number(cell.slice(8, 10))}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          ))}

          {withTime ? (
            <View style={styles.timeRow}>
              <Text style={[styles.timeLabel, { color: colors.inkMuted }]}>时间</Text>
              <Stepper
                label={time ? time.slice(0, 2) : '--'}
                onMinus={() => shiftTime(-1, 0)}
                onPlus={() => shiftTime(1, 0)}
              />
              <Text style={[styles.colon, { color: colors.ink }]}>:</Text>
              <Stepper
                label={time ? time.slice(3, 5) : '--'}
                onMinus={() => shiftTime(0, -5)}
                onPlus={() => shiftTime(0, 5)}
              />
              {time ? (
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="清除时间"
                  onPress={() => onChangeTime(null)}
                  style={styles.clearTime}>
                  <Text style={[styles.clearTimeText, { color: colors.inkMuted }]}>清除</Text>
                </Pressable>
              ) : null}
            </View>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

function Quick({ label, onPress }: { label: string; onPress: () => void }) {
  const { colors } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      style={[styles.quick, { borderColor: colors.line }]}>
      <Text style={[styles.quickText, { color: colors.ink }]}>{label}</Text>
    </Pressable>
  );
}

function Stepper({
  label,
  onMinus,
  onPlus,
}: {
  label: string;
  onMinus: () => void;
  onPlus: () => void;
}) {
  const { colors } = useTheme();
  return (
    <View style={styles.stepper}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="减少"
        onPress={onMinus}
        style={[styles.stepperBtn, { borderColor: colors.line }]}>
        <Text style={[styles.stepperBtnText, { color: colors.ink }]}>−</Text>
      </Pressable>
      <Text style={[styles.stepperValue, { color: colors.ink }]}>{label}</Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="增加"
        onPress={onPlus}
        style={[styles.stepperBtn, { borderColor: colors.line }]}>
        <Text style={[styles.stepperBtnText, { color: colors.ink }]}>＋</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: Space.sm,
  },
  label: {
    fontSize: Type.small,
  },
  summary: {
    minHeight: 44,
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  summaryText: {
    fontSize: Type.body,
    flex: 1,
  },
  caret: {
    fontSize: Type.small,
  },
  panel: {
    borderWidth: 1,
    borderRadius: Radius.md,
    padding: Space.md,
    gap: Space.sm,
  },
  quickRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  quick: {
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.md,
    minHeight: 32,
    justifyContent: 'center',
  },
  quickText: {
    fontSize: Type.small,
  },
  monthHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  monthBtn: {
    width: 32,
    height: 32,
    borderWidth: 1,
    borderRadius: Radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  monthBtnText: {
    fontSize: Type.bodyLg,
  },
  monthLabel: {
    fontSize: Type.body,
    fontFamily: 'IBMPlexMono_500Medium',
  },
  weekHeader: {
    flexDirection: 'row',
  },
  weekday: {
    flex: 1,
    textAlign: 'center',
    fontSize: Type.micro,
  },
  weekRow: {
    flexDirection: 'row',
  },
  dayEmpty: {
    flex: 1,
    height: 34,
    margin: 1,
  },
  dayCell: {
    flex: 1,
    height: 34,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: Radius.sm,
    margin: 1,
  },
  dayText: {
    fontSize: Type.small,
    fontFamily: 'IBMPlexMono_400Regular',
  },
  timeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
    paddingTop: Space.xs,
    flexWrap: 'wrap',
  },
  timeLabel: {
    fontSize: Type.small,
    minWidth: 32,
  },
  colon: {
    fontSize: Type.body,
  },
  stepper: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
  },
  stepperBtn: {
    width: 32,
    height: 32,
    borderWidth: 1,
    borderRadius: Radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepperBtnText: {
    fontSize: Type.body,
  },
  stepperValue: {
    minWidth: 30,
    textAlign: 'center',
    fontSize: Type.body,
    fontFamily: 'IBMPlexMono_500Medium',
  },
  clearTime: {
    paddingHorizontal: Space.sm,
    minHeight: 32,
    justifyContent: 'center',
  },
  clearTimeText: {
    fontSize: Type.small,
  },
});
