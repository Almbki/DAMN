import { useEffect, useMemo, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
  type LayoutChangeEvent,
} from 'react-native';

import { hhmm } from '@/api/format';
import type { ScheduleEventRead } from '@/api/types';
import {
  WEEKDAY_LABELS,
  eventTimeRange,
  monthDay,
  weekdayIndex,
} from '@/components/schedule/format';
import { useInteraction } from '@/components/ui/interaction';
import {
  Elevation,
  Fonts,
  Layout,
  Radius,
  Space,
  Type,
  type ThemeColors,
} from '@/constants/tokens';
import { addDays, todayISO } from '@/domain/date';
import type { Task } from '@/domain/task';
import { useTheme } from '@/state/theme';

const START_HOUR = 6;
const END_HOUR = 24;
const HOURS = END_HOUR - START_HOUR;

/** Half-hour slots: fine enough for real timetable times, still calm to read. */
const SLOT_MINUTES = 30;
const SLOTS_PER_HOUR = 60 / SLOT_MINUTES;
const SLOT_HEIGHT = 24;
const HOUR_HEIGHT = SLOT_HEIGHT * SLOTS_PER_HOUR;
const SLOT_COUNT = HOURS * SLOTS_PER_HOUR;
const GRID_HEIGHT = HOURS * HOUR_HEIGHT;

const DAY_START = START_HOUR * 60;
const DAY_END = END_HOUR * 60;
const AXIS_WIDTH = 52;
const HEADER_HEIGHT = 48;
const DAY_MIN_WIDTH = 104;
const MIN_BLOCK_HEIGHT = 30;
/** Rounded up from the 30px minimum so lane layout matches the drawn block. */
const MIN_LAYOUT_MINUTES = Math.ceil((MIN_BLOCK_HEIGHT / HOUR_HEIGHT) * 60);
const LANE_GAP = 3;
const BLOCK_INSET = 4;
const DEFAULT_TASK_MINUTES = 30;

/** One text line inside a block; the visibility maths below mirrors the styles. */
const BLOCK_LINE_HEIGHT = 14;
const BLOCK_GAP = 1;

const HOUR_MARKS = Array.from({ length: HOURS + 1 }, (_, index) => START_HOUR + index);
const SLOT_MARKS = Array.from({ length: SLOT_COUNT + 1 }, (_, index) => index);

type EventOccurrence = {
  kind: 'event';
  event: ScheduleEventRead;
  start: number;
  end: number;
};

type TaskOccurrence = {
  kind: 'task';
  task: Task;
  start: number;
  end: number;
};

type Occurrence = EventOccurrence | TaskOccurrence;

type Block = Occurrence & {
  lane: number;
  lanes: number;
};

type BlockPalette = {
  background: string;
  foreground: string;
  accent: string;
};

function startMinutes(event: ScheduleEventRead): number {
  const [hours, minutes] = hhmm(event.start_time).split(':');
  return (Number(hours) || 0) * 60 + (Number(minutes) || 0);
}

function endMinutes(event: ScheduleEventRead): number {
  const [hours, minutes] = hhmm(event.end_time).split(':');
  const value = (Number(hours) || 0) * 60 + (Number(minutes) || 0);
  // 00:00 at the end of a course means midnight, not the start of the day.
  return value === 0 ? DAY_END : value;
}

function parseClock(value: string | null | undefined): number | null {
  const text = hhmm(value);
  if (!text) return null;
  const match = /^(\d{1,2}):(\d{2})$/.exec(text);
  if (!match) return null;
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours > 23 || minutes > 59) return null;
  return hours * 60 + minutes;
}

function minutesNow(now: Date): number {
  return now.getHours() * 60 + now.getMinutes();
}

function clockLabel(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
}

function occurrenceId(item: Occurrence): number {
  return item.kind === 'event' ? item.event.id : item.task.id;
}

function compareOccurrences(a: Occurrence, b: Occurrence): number {
  if (a.start !== b.start) return a.start - b.start;
  if (a.end !== b.end) return a.end - b.end;
  if (a.kind !== b.kind) return a.kind === 'event' ? -1 : 1;
  return occurrenceId(a) - occurrenceId(b);
}

/** Backend occurrence rules: bounded one-offs repeat daily; weekdays filter. */
function occursOn(event: ScheduleEventRead, day: string): boolean {
  const start = event.start_date ? event.start_date.slice(0, 10) : null;
  const end = event.end_date ? event.end_date.slice(0, 10) : start;
  if (start && day < start) return false;
  if (end && day > end) return false;

  const weekdays = (event.weekdays ?? []).filter((value) => value >= 0 && value <= 6);
  if (weekdays.length === 0) return start != null;
  return weekdays.includes(weekdayIndex(day));
}

/** Clamp to the 06:00–24:00 grid; overnight events end at midnight. */
function toEventOccurrence(event: ScheduleEventRead): EventOccurrence | null {
  const start = startMinutes(event);
  let end = endMinutes(event);
  // A later-looking end means the course crosses midnight.
  if (end < start) end = DAY_END;
  if (end === start) return null;
  if (end <= DAY_START || start >= DAY_END) return null;
  const clippedStart = Math.max(start, DAY_START);
  const clippedEnd = Math.min(end, DAY_END);
  if (clippedEnd <= clippedStart) return null;
  return { kind: 'event', event, start: clippedStart, end: clippedEnd };
}

/** The date a planned task belongs to for timetable purposes. */
export function taskDay(task: Task): string | null {
  return task.dueDate ?? task.occurrenceDate;
}

/** Tasks whose planned day is inside the visible Monday–Sunday week. */
export function tasksForWeek(tasks: Task[], weekStart: string): Task[] {
  const weekEnd = addDays(weekStart, 6);
  return tasks.filter((task) => {
    const day = taskDay(task);
    return day != null && day >= weekStart && day <= weekEnd;
  });
}

/**
 * Planned tasks use `startTime` (or `dueTime`), then `endTime`, then the
 * estimate, then a 30-minute default. Like events, they are clipped to the
 * 06:00–24:00 grid; anything unplaceable falls through to the untimed list.
 */
function toTaskOccurrence(task: Task): TaskOccurrence | null {
  const start = parseClock(task.startTime ?? task.dueTime);
  if (start == null) return null;

  const fallbackMinutes =
    task.estimatedMinutes != null && task.estimatedMinutes > 0
      ? task.estimatedMinutes
      : DEFAULT_TASK_MINUTES;
  let end = start + fallbackMinutes;

  if (task.endTime) {
    const explicitEnd = parseClock(task.endTime);
    if (explicitEnd === 0) {
      // 00:00 means midnight at the end of a task, not the start of the day.
      end = DAY_END;
    } else if (explicitEnd != null && explicitEnd > start) {
      end = explicitEnd;
    }
  }

  if (end <= DAY_START || start >= DAY_END) return null;
  const clippedStart = Math.max(start, DAY_START);
  const clippedEnd = Math.min(end, DAY_END);
  if (clippedEnd <= clippedStart) return null;
  return { kind: 'task', task, start: clippedStart, end: clippedEnd };
}

function buildDayOccurrences(
  events: ScheduleEventRead[],
  weekTasks: Task[],
  day: string,
): Occurrence[] {
  const items: Occurrence[] = [];
  events.forEach((event) => {
    if (!occursOn(event, day)) return;
    const occurrence = toEventOccurrence(event);
    if (occurrence) items.push(occurrence);
  });
  weekTasks.forEach((task) => {
    if (taskDay(task) !== day) return;
    const occurrence = toTaskOccurrence(task);
    if (occurrence) items.push(occurrence);
  });
  return items.sort(compareOccurrences);
}

/**
 * Greedy lane assignment inside each transitive overlap cluster. Touching
 * endpoints do not overlap, so back-to-back courses keep the full column.
 */
function layoutDay(items: Occurrence[]): Block[] {
  const sorted = [...items].sort(compareOccurrences);
  const result: Block[] = [];
  let cluster: { occurrence: Occurrence; lane: number }[] = [];
  let laneEnds: number[] = [];
  let clusterEnd = 0;

  const flush = () => {
    if (cluster.length === 0) return;
    const lanes = laneEnds.length;
    cluster.forEach((entry) => result.push({ ...entry.occurrence, lane: entry.lane, lanes }));
    cluster = [];
    laneEnds = [];
    clusterEnd = 0;
  };

  sorted.forEach((occurrence) => {
    // Very short blocks are drawn at the 30px floor. Reserve that much vertical
    // space so two back-to-back 15-minute items become lanes, not a cover-up.
    const drawnEnd = Math.min(
      DAY_END,
      Math.max(occurrence.end, occurrence.start + MIN_LAYOUT_MINUTES),
    );
    if (cluster.length > 0 && occurrence.start >= clusterEnd) flush();

    let lane = laneEnds.findIndex((end) => end <= occurrence.start);
    if (lane === -1) {
      lane = laneEnds.length;
      laneEnds.push(drawnEnd);
    } else {
      laneEnds[lane] = drawnEnd;
    }
    cluster.push({ occurrence, lane });
    clusterEnd = Math.max(clusterEnd, drawnEnd);
  });
  flush();

  return result;
}

function kindPalette(kind: string, colors: ThemeColors): BlockPalette {
  if (kind === 'exam') {
    return {
      background: colors.warningContainer,
      foreground: colors.onWarningContainer,
      accent: colors.warning,
    };
  }
  if (kind === 'busy') {
    return {
      background: colors.surfaceContainerHigh,
      foreground: colors.ink,
      accent: colors.outline,
    };
  }
  if (kind === 'other') {
    return {
      background: colors.surfaceContainer,
      foreground: colors.ink,
      accent: colors.outline,
    };
  }
  return {
    background: colors.primaryContainer,
    foreground: colors.onPrimaryContainer,
    accent: colors.primary,
  };
}

/** Tasks read as a secondary surface, never as an imported course. */
function taskPalette(task: Task, colors: ThemeColors): BlockPalette {
  if (task.done || task.skipped) {
    return {
      background: colors.surfaceContainer,
      foreground: colors.inkMuted,
      accent: colors.outlineVariant,
    };
  }
  return {
    background: colors.secondaryContainer,
    foreground: colors.onSecondaryContainer,
    accent: colors.secondary,
  };
}

export function CourseTimetable({
  events,
  tasks,
  weekStart,
  onSelect,
  onSelectTask,
  onImport,
}: {
  events: ScheduleEventRead[];
  tasks: Task[];
  /** Monday of the visible week. */
  weekStart: string;
  onSelect: (event: ScheduleEventRead) => void;
  onSelectTask: (task: Task) => void;
  onImport?: () => void;
}) {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const isMobile = width > 0 && width < Layout.breakpoint;

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, index) => addDays(weekStart, index)),
    [weekStart],
  );

  const weekTasks = useMemo(() => tasksForWeek(tasks, weekStart), [tasks, weekStart]);
  // Undated tasks belong to no week, so they must stay reachable while the
  // timetable is expanded instead of disappearing with the daily list.
  const noDateTasks = useMemo(() => tasks.filter((task) => taskDay(task) == null), [tasks]);

  const dayBlocks = useMemo(
    () => days.map((day) => layoutDay(buildDayOccurrences(events, weekTasks, day))),
    [days, events, weekTasks],
  );

  const untimedTasks = useMemo(
    () =>
      [...weekTasks, ...noDateTasks]
        .filter((task) => taskDay(task) == null || toTaskOccurrence(task) == null)
        .sort((a, b) => a.order - b.order || a.id - b.id),
    [weekTasks, noDateTasks],
  );

  const hasPlacedContent = dayBlocks.some((blocks) => blocks.length > 0);

  return (
    <View style={styles.root}>
      {/* Even a week with no imported courses keeps a usable timetable shell:
          planned tasks may still exist, and an empty grid is clearer than a
          disappearing section. */}
      {isMobile ? (
        <MobileAgenda
          days={days}
          dayBlocks={dayBlocks}
          onSelectEvent={onSelect}
          onSelectTask={onSelectTask}
        />
      ) : (
        <DesktopTimetable
          days={days}
          dayBlocks={dayBlocks}
          onSelectEvent={onSelect}
          onSelectTask={onSelectTask}
        />
      )}
      {!hasPlacedContent && untimedTasks.length === 0 ? (
        <Text style={[styles.emptyWeek, { color: colors.inkMuted }]}>
          本周暂无课程或任务安排。
        </Text>
      ) : null}

      {untimedTasks.length > 0 ? (
        <UntimedTasks tasks={untimedTasks} onSelectTask={onSelectTask} />
      ) : null}
    </View>
  );
}

function UntimedTasks({
  tasks,
  onSelectTask,
}: {
  tasks: Task[];
  onSelectTask: (task: Task) => void;
}) {
  const { colors } = useTheme();

  return (
    <View
      style={[
        styles.untimed,
        {
          borderColor: colors.outlineVariant,
          backgroundColor: colors.surfaceContainerLow,
        },
      ]}>
      <View style={styles.untimedHeader}>
        <Text style={[styles.untimedTitle, { color: colors.ink }]}>未排时间</Text>
        <Text style={[styles.untimedCount, { color: colors.inkMuted }]}>{tasks.length} 件</Text>
      </View>

      {tasks.map((task, index) => {
        const day = taskDay(task);
        const dayLabel = day ? `${WEEKDAY_LABELS[weekdayIndex(day)]} ${monthDay(day)}` : '';
        const status = task.done ? '已完成' : task.skipped ? '已跳过' : '待安排';
        return (
          <Pressable
            key={task.id}
            accessibilityRole="button"
            accessibilityLabel={`任务详情：${task.title}${dayLabel ? `，${dayLabel}` : ''}，${status}`}
            onPress={() => onSelectTask(task)}
            style={({ pressed }) => [
              styles.untimedRow,
              index > 0
                ? { borderTopColor: colors.outlineVariant, borderTopWidth: 1 }
                : null,
              { opacity: pressed ? 0.72 : 1 },
            ]}>
            <Text
              numberOfLines={2}
              style={[
                styles.untimedTask,
                {
                  color: task.done || task.skipped ? colors.inkMuted : colors.ink,
                  textDecorationLine: task.done ? 'line-through' : 'none',
                },
              ]}>
              {task.title}
            </Text>
            <Text
              style={[
                styles.untimedMeta,
                { color: task.skipped ? colors.warning : colors.inkMuted },
              ]}>
              {dayLabel ? `${dayLabel} · ${status}` : status}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function useNowMinutes() {
  const [nowMinutes, setNowMinutes] = useState(() => minutesNow(new Date()));

  useEffect(() => {
    // Keep the now-line moving without re-rendering every second.
    const timer = setInterval(() => setNowMinutes(minutesNow(new Date())), 60_000);
    return () => clearInterval(timer);
  }, []);

  return nowMinutes;
}

function DesktopTimetable({
  days,
  dayBlocks,
  onSelectEvent,
  onSelectTask,
}: {
  days: string[];
  dayBlocks: Block[][];
  onSelectEvent: (event: ScheduleEventRead) => void;
  onSelectTask: (task: Task) => void;
}) {
  const { colors } = useTheme();
  const [availableWidth, setAvailableWidth] = useState(0);
  const nowMinutes = useNowMinutes();

  const today = todayISO();
  const todayIndex = days.indexOf(today);
  const showNow = todayIndex >= 0 && nowMinutes >= DAY_START && nowMinutes <= DAY_END;

  // A day with three overlapping items gets a wider column instead of three
  // unreadable slivers; the grid scrolls horizontally when that happens.
  const maxLanes = dayBlocks.reduce(
    (max, blocks) => blocks.reduce((laneMax, block) => Math.max(laneMax, block.lanes), max),
    1,
  );
  const denseDayWidth =
    maxLanes * 48 + BLOCK_INSET * 2 + (maxLanes - 1) * LANE_GAP + 1;
  const fittedDayWidth =
    availableWidth > AXIS_WIDTH + 2 ? (availableWidth - AXIS_WIDTH - 2) / 7 : 0;
  const dayWidth = Math.max(DAY_MIN_WIDTH, denseDayWidth, fittedDayWidth);
  const daysWidth = dayWidth * 7;

  const onLayout = (event: LayoutChangeEvent) => {
    const width = event.nativeEvent.layout.width;
    setAvailableWidth((current) => (current === width ? current : width));
  };

  return (
    <View
      onLayout={onLayout}
      accessibilityLabel="课程表，周一到周日，06:00 到 24:00"
      style={[
        styles.frame,
        {
          borderColor: colors.outlineVariant,
          backgroundColor: colors.surfaceContainerLowest,
        },
      ]}>
      <View
        style={[
          styles.axis,
          {
            width: AXIS_WIDTH,
            borderRightColor: colors.outlineVariant,
            backgroundColor: colors.surfaceContainerLow,
          },
        ]}
        importantForAccessibility="no-hide-descendants">
        <View
          style={[
            styles.axisHeader,
            {
              height: HEADER_HEIGHT,
              borderBottomColor: colors.outlineVariant,
              backgroundColor: colors.surfaceContainerLow,
            },
          ]}
        />
        <View style={[styles.axisBody, { height: GRID_HEIGHT }]}>
          {HOUR_MARKS.map((hour, index) => (
            <Text
              key={hour}
              style={[
                styles.hourLabel,
                {
                  top:
                    index === 0
                      ? 0
                      : index === HOURS
                        ? GRID_HEIGHT - 16
                        : index * HOUR_HEIGHT - 8,
                  color: colors.inkFaint,
                },
              ]}>
              {String(hour).padStart(2, '0')}:00
            </Text>
          ))}
        </View>
      </View>

      <ScrollView
        horizontal
        nestedScrollEnabled
        directionalLockEnabled
        showsHorizontalScrollIndicator={false}
        style={styles.scroll}>
        <View style={{ width: daysWidth }}>
          <View
            style={[
              styles.headerRow,
              {
                height: HEADER_HEIGHT,
                borderBottomColor: colors.outlineVariant,
                backgroundColor: colors.surfaceContainerLow,
              },
            ]}>
            {days.map((day, index) => {
              const isToday = day === today;
              return (
                <View
                  key={day}
                  accessibilityLabel={`${WEEKDAY_LABELS[index]}，${monthDay(day)}`}
                  style={[
                    styles.dayHeader,
                    {
                      width: dayWidth,
                      borderRightColor: colors.outlineVariant,
                      borderRightWidth: index === 6 ? 0 : 1,
                    },
                  ]}>
                  <Text
                    style={[
                      styles.weekday,
                      { color: isToday ? colors.primary : colors.ink },
                    ]}>
                    {WEEKDAY_LABELS[index]}
                  </Text>
                  <Text
                    style={[
                      styles.dayDate,
                      { color: isToday ? colors.primary : colors.inkMuted },
                    ]}>
                    {monthDay(day)}
                  </Text>
                  {isToday ? (
                    <View style={[styles.todayDot, { backgroundColor: colors.now }]} />
                  ) : null}
                </View>
              );
            })}
          </View>

          <View style={[styles.bodyRow, { height: GRID_HEIGHT }]}>
            {days.map((day, index) => (
              <View
                key={day}
                style={[
                  styles.dayColumn,
                  {
                    width: dayWidth,
                    backgroundColor:
                      index >= 5 ? colors.surfaceContainerLow : colors.surfaceContainerLowest,
                    borderRightColor: colors.outlineVariant,
                    borderRightWidth: index === 6 ? 0 : 1,
                  },
                ]}>
                <GridLines
                  lineColor={colors.outlineVariant}
                  strongColor={colors.outline}
                />
                {dayBlocks[index].map((block) => (
                  <ScheduleBlock
                    key={`${block.kind}-${occurrenceId(block)}-${day}-${block.lane}`}
                    block={block}
                    day={day}
                    dayWidth={dayWidth}
                    onSelectEvent={onSelectEvent}
                    onSelectTask={onSelectTask}
                  />
                ))}
                {showNow && index === todayIndex ? (
                  <NowMarker
                    top={((nowMinutes - DAY_START) / 60) * HOUR_HEIGHT}
                    label={clockLabel(nowMinutes)}
                  />
                ) : null}
              </View>
            ))}
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

function MobileAgenda({
  days,
  dayBlocks,
  onSelectEvent,
  onSelectTask,
}: {
  days: string[];
  dayBlocks: Block[][];
  onSelectEvent: (event: ScheduleEventRead) => void;
  onSelectTask: (task: Task) => void;
}) {
  const { colors } = useTheme();
  const today = todayISO();
  const filled = days
    .map((day, index) => ({ day, index, blocks: dayBlocks[index] }))
    .filter((entry) => entry.blocks.length > 0);
  const emptyCount = days.length - filled.length;

  return (
    <View
      style={[
        styles.agenda,
        {
          borderColor: colors.outlineVariant,
          backgroundColor: colors.surfaceContainerLowest,
        },
      ]}>
      {filled.map((entry, position) => {
        const isToday = entry.day === today;
        return (
          <View
            key={entry.day}
            style={[
              styles.agendaDay,
              position > 0
                ? { borderTopColor: colors.outlineVariant, borderTopWidth: 1 }
                : null,
            ]}>
            <View
              style={[
                styles.agendaDayHeader,
                { borderBottomColor: colors.outlineVariant },
              ]}>
              <Text
                style={[
                  styles.agendaWeekday,
                  { color: isToday ? colors.primary : colors.ink },
                ]}>
                {isToday ? `今天 · ${WEEKDAY_LABELS[entry.index]}` : WEEKDAY_LABELS[entry.index]}
              </Text>
              <Text
                style={[
                  styles.agendaDayDate,
                  { color: isToday ? colors.primary : colors.inkMuted },
                ]}>
                {monthDay(entry.day)}
              </Text>
            </View>

            <View style={styles.agendaItems}>
              {entry.blocks.map((block) => (
                <AgendaRow
                  key={`${block.kind}-${occurrenceId(block)}-${entry.day}`}
                  block={block}
                  day={entry.day}
                  onSelectEvent={onSelectEvent}
                  onSelectTask={onSelectTask}
                />
              ))}
            </View>
          </View>
        );
      })}

      {emptyCount > 0 ? (
        <Text style={[styles.agendaEmpty, { color: colors.inkFaint }]}>
          其余 {emptyCount} 天暂无安排
        </Text>
      ) : null}
    </View>
  );
}

function AgendaRow({
  block,
  day,
  onSelectEvent,
  onSelectTask,
}: {
  block: Block;
  day: string;
  onSelectEvent: (event: ScheduleEventRead) => void;
  onSelectTask: (task: Task) => void;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const isEvent = block.kind === 'event';
  const palette = isEvent
    ? kindPalette(block.event.event_kind, colors)
    : taskPalette(block.task, colors);
  const done = !isEvent && block.task.done;
  const skipped = !isEvent && block.task.skipped;
  const title = isEvent ? block.event.title : block.task.title;
  const location = isEvent ? (block.event.location ?? '').trim() : '';
  const teacher = isEvent ? (block.event.teacher ?? '').trim() : '';
  const weekday = WEEKDAY_LABELS[weekdayIndex(day)];
  const timeRange = `${clockLabel(block.start)}–${clockLabel(block.end)}`;

  const meta = isEvent
    ? [location, teacher].filter(Boolean).join(' · ')
    : ['任务', done ? '已完成' : skipped ? '已跳过' : block.task.estimatedMinutes ? `${block.task.estimatedMinutes} 分钟` : '']
        .filter(Boolean)
        .join(' · ');

  const label = isEvent
    ? `${block.event.title}，${weekday} ${monthDay(day)}，${eventTimeRange(block.event)}${
        location ? `，地点 ${location}` : ''
      }${teacher ? `，教师 ${teacher}` : ''}`
    : `任务：${block.task.title}，${weekday} ${monthDay(day)}，${timeRange}${
        done ? '，已完成' : skipped ? '，已跳过' : ''
      }`;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint={isEvent ? '点按查看日程详情或删除' : '点按查看任务详情'}
      onPress={() =>
        isEvent ? onSelectEvent(block.event) : onSelectTask(block.task)
      }
      focusable
      {...handlers}
      style={({ pressed }) => [
        styles.agendaRow,
        { opacity: pressed ? 0.8 : hovered ? 0.94 : 1 },
      ]}>
      <View style={styles.agendaTime}>
        <Text style={[styles.agendaStart, { color: colors.ink }]}>
          {clockLabel(block.start)}
        </Text>
        <Text style={[styles.agendaEnd, { color: colors.inkFaint }]}>
          {clockLabel(block.end)}
        </Text>
      </View>

      <View
        style={[
          styles.agendaCard,
          {
            backgroundColor: palette.background,
            borderLeftColor: palette.accent,
            boxShadow: focused ? `inset 0 0 0 2px ${colors.focusRing}` : undefined,
          },
        ]}>
        <Text
          numberOfLines={2}
          ellipsizeMode="tail"
          style={[
            styles.agendaTitle,
            {
              color: palette.foreground,
              textDecorationLine: done ? 'line-through' : 'none',
            },
          ]}>
          {done ? `✓ ${title}` : title}
        </Text>
        {meta ? (
          <Text
            numberOfLines={1}
            ellipsizeMode="tail"
            style={[
              styles.agendaMeta,
              { color: skipped ? colors.warning : palette.foreground },
            ]}>
            {meta}
          </Text>
        ) : null}
      </View>
    </Pressable>
  );
}

function GridLines({
  lineColor,
  strongColor,
}: {
  lineColor: string;
  strongColor: string;
}) {
  return (
    <>
      {SLOT_MARKS.map((slot) => {
        const isHour = slot % SLOTS_PER_HOUR === 0;
        const isEdge = slot === 0 || slot === SLOT_COUNT;
        return (
          <View
            key={slot}
            pointerEvents="none"
            style={[
              styles.gridLine,
              {
                top: slot * SLOT_HEIGHT,
                backgroundColor: isEdge ? strongColor : lineColor,
                opacity: isEdge ? 0.75 : isHour ? 0.55 : 0.3,
              },
            ]}
          />
        );
      })}
    </>
  );
}

function NowMarker({ top, label }: { top: number; label: string }) {
  const { colors } = useTheme();
  // At the very top of the grid the label would be clipped by the column edge.
  const labelTop = top < 12 ? 3 : -8;

  return (
    <View
      accessible
      accessibilityRole="timer"
      accessibilityLabel={`当前时间 ${label}`}
      pointerEvents="none"
      style={[styles.nowMarker, { top }]}>
      <View style={[styles.nowBar, { backgroundColor: colors.now }]} />
      <View
        style={[
          styles.nowDot,
          { backgroundColor: colors.now, borderColor: colors.surfaceContainerLowest },
        ]}
      />
      <Text
        accessible={false}
        importantForAccessibility="no"
        style={[
          styles.nowLabel,
          {
            top: labelTop,
            color: colors.onNow,
            backgroundColor: colors.nowContainer,
            borderColor: colors.now,
          },
        ]}>
        {label}
      </Text>
    </View>
  );
}

function ScheduleBlock({
  block,
  day,
  dayWidth,
  onSelectEvent,
  onSelectTask,
}: {
  block: Block;
  day: string;
  dayWidth: number;
  onSelectEvent: (event: ScheduleEventRead) => void;
  onSelectTask: (task: Task) => void;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const isEvent = block.kind === 'event';
  const palette = isEvent
    ? kindPalette(block.event.event_kind, colors)
    : taskPalette(block.task, colors);
  const done = !isEvent && block.task.done;
  const skipped = !isEvent && block.task.skipped;
  const title = isEvent ? block.event.title : block.task.title;
  const location = isEvent ? (block.event.location ?? '').trim() : '';
  const teacher = isEvent ? (block.event.teacher ?? '').trim() : '';

  const gap = block.lanes > 1 ? LANE_GAP : 0;
  const laneWidth = (dayWidth - BLOCK_INSET * 2 - gap * (block.lanes - 1)) / block.lanes;
  const left = BLOCK_INSET + block.lane * (laneWidth + gap);
  const top = ((block.start - DAY_START) / 60) * HOUR_HEIGHT + 1;
  const height = Math.max(
    MIN_BLOCK_HEIGHT,
    ((block.end - block.start) / 60) * HOUR_HEIGHT - 2,
  );

  const titleSize = laneWidth < 62 ? Type.labelSmall : Type.labelMedium;
  const weekday = WEEKDAY_LABELS[weekdayIndex(day)];
  const taskMeta =
    !isEvent && (done || skipped || block.task.estimatedMinutes)
      ? [
          done ? '已完成' : skipped ? '已跳过' : '',
          block.task.estimatedMinutes ? `${block.task.estimatedMinutes} 分钟` : '',
        ]
          .filter(Boolean)
          .join(' · ')
      : '';
  const timeRange = `${clockLabel(block.start)}–${clockLabel(block.end)}`;

  // Fit the title first, then spend whatever height is left on location and
  // teacher (events) or status and duration (tasks). Blocks are never stretched
  // or snapped to a slot.
  const contentHeight = Math.max(0, height - Space.xs * 2);
  const titleLines =
    contentHeight >= BLOCK_LINE_HEIGHT * 2 + BLOCK_GAP + BLOCK_LINE_HEIGHT ? 2 : 1;
  const remaining =
    contentHeight - (titleLines * BLOCK_LINE_HEIGHT + (titleLines - 1) * BLOCK_GAP);
  const showLocation = location.length > 0 && remaining >= BLOCK_GAP + BLOCK_LINE_HEIGHT;
  const showTeacher =
    teacher.length > 0 &&
    remaining - (showLocation ? BLOCK_GAP + BLOCK_LINE_HEIGHT : 0) >=
      BLOCK_GAP + BLOCK_LINE_HEIGHT;
  const showTaskMeta = taskMeta.length > 0 && remaining >= BLOCK_GAP + BLOCK_LINE_HEIGHT;

  const label = isEvent
    ? `${block.event.title}，${weekday} ${monthDay(day)}，${eventTimeRange(block.event)}${
        location ? `，地点 ${location}` : ''
      }${teacher ? `，教师 ${teacher}` : ''}`
    : `任务：${block.task.title}，${weekday} ${monthDay(day)}，${timeRange}${
        done ? '，已完成' : skipped ? '，已跳过' : ''
      }`;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint={isEvent ? '点按查看日程详情或删除' : '点按查看任务详情'}
      onPress={() =>
        isEvent ? onSelectEvent(block.event) : onSelectTask(block.task)
      }
      hitSlop={8}
      focusable
      {...handlers}
      style={({ pressed }) => [
        styles.event,
        {
          top,
          left,
          width: laneWidth,
          height,
          backgroundColor: palette.background,
          borderLeftColor: palette.accent,
          opacity: pressed ? 0.84 : hovered ? 0.94 : 1,
          boxShadow: focused
            ? `inset 0 0 0 2px ${colors.focusRing}`
            : Elevation.highlight,
        },
      ]}>
      <Text
        numberOfLines={titleLines}
        ellipsizeMode="tail"
        style={[
          styles.eventTitle,
          {
            color: palette.foreground,
            fontSize: titleSize,
            textDecorationLine: done ? 'line-through' : 'none',
          },
        ]}>
        {done ? `✓ ${title}` : title}
      </Text>
      {showLocation ? (
        <Text
          numberOfLines={1}
          ellipsizeMode="tail"
          style={[styles.eventMeta, { color: palette.foreground }]}>
          {location}
        </Text>
      ) : null}
      {showTeacher ? (
        <Text
          numberOfLines={1}
          ellipsizeMode="tail"
          style={[styles.eventMeta, { color: palette.foreground }]}>
          {teacher}
        </Text>
      ) : null}
      {showTaskMeta ? (
        <Text
          numberOfLines={1}
          ellipsizeMode="tail"
          style={[
            styles.eventMeta,
            { color: skipped ? colors.warning : palette.foreground },
          ]}>
          {taskMeta}
        </Text>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: Space.md,
  },
  frame: {
    flexDirection: 'row',
    borderWidth: 1,
    borderRadius: Radius.md,
    overflow: 'hidden',
  },
  axis: {
    borderRightWidth: 1,
  },
  axisHeader: {
    borderBottomWidth: 1,
  },
  axisBody: {
    position: 'relative',
  },
  hourLabel: {
    position: 'absolute',
    right: Space.sm,
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelSmall,
    lineHeight: 16,
  },
  scroll: {
    flex: 1,
    minWidth: 0,
  },
  headerRow: {
    flexDirection: 'row',
    borderBottomWidth: 1,
  },
  dayHeader: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 1,
  },
  weekday: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  dayDate: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelSmall,
  },
  todayDot: {
    position: 'absolute',
    top: Space.xs + 2,
    right: Space.sm,
    width: 5,
    height: 5,
    borderRadius: 3,
  },
  bodyRow: {
    flexDirection: 'row',
  },
  dayColumn: {
    position: 'relative',
    overflow: 'hidden',
  },
  gridLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 1,
  },
  nowMarker: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
    zIndex: 3,
  },
  nowBar: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: 0,
    height: 2,
    borderRadius: 1,
  },
  nowDot: {
    position: 'absolute',
    left: 0,
    top: -3,
    width: 8,
    height: 8,
    borderRadius: 4,
    borderWidth: 1.5,
  },
  nowLabel: {
    position: 'absolute',
    right: 2,
    fontFamily: Fonts.mono,
    fontSize: Type.micro,
    lineHeight: 13,
    paddingHorizontal: 3,
    borderWidth: 1,
    borderRadius: Radius.xs,
    overflow: 'hidden',
    textAlign: 'center',
  },
  event: {
    position: 'absolute',
    paddingHorizontal: Space.xs + 1,
    paddingVertical: Space.xs,
    gap: BLOCK_GAP,
    borderLeftWidth: 3,
    borderRadius: Radius.xs,
    overflow: 'hidden',
  },
  eventTitle: {
    fontWeight: '600',
    lineHeight: BLOCK_LINE_HEIGHT,
  },
  eventMeta: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelSmall,
    lineHeight: BLOCK_LINE_HEIGHT,
  },
  notice: {
    borderWidth: 1,
    borderRadius: Radius.md,
    padding: Space.md,
    gap: Space.xs,
  },
  noticeTitle: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
  },
  noticeBody: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * 1.5,
  },
  untimed: {
    borderWidth: 1,
    borderRadius: Radius.md,
    overflow: 'hidden',
  },
  untimedHeader: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
    paddingHorizontal: Space.md,
    paddingVertical: Space.sm,
  },
  untimedTitle: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
  },
  untimedCount: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelSmall,
  },
  untimedRow: {
    paddingHorizontal: Space.md,
    paddingVertical: Space.sm,
    gap: 2,
  },
  untimedTask: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * 1.4,
  },
  untimedMeta: {
    fontSize: Type.labelSmall,
    lineHeight: Type.labelSmall * 1.4,
  },
  agenda: {
    borderWidth: 1,
    borderRadius: Radius.md,
    overflow: 'hidden',
  },
  agendaDay: {
    paddingHorizontal: Space.md,
    paddingTop: Space.md,
    paddingBottom: Space.sm,
  },
  agendaDayHeader: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
    borderBottomWidth: 1,
    paddingBottom: Space.xs,
    marginBottom: Space.sm,
  },
  agendaWeekday: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
  },
  agendaDayDate: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelSmall,
  },
  agendaItems: {
    gap: Space.sm,
  },
  agendaRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Space.md,
  },
  agendaTime: {
    width: 46,
    alignItems: 'flex-end',
    paddingTop: 3,
    gap: 1,
  },
  agendaStart: {
    fontFamily: Fonts.mono,
    fontSize: Type.labelMedium,
  },
  agendaEnd: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.micro,
  },
  agendaCard: {
    flex: 1,
    minWidth: 0,
    borderLeftWidth: 3,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.sm,
    paddingVertical: Space.xs + 1,
    gap: 1,
  },
  agendaTitle: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
    lineHeight: Type.labelLarge * 1.3,
  },
  agendaMeta: {
    fontSize: Type.labelSmall,
    lineHeight: Type.labelSmall * 1.35,
  },
  agendaEmpty: {
    fontSize: Type.labelSmall,
    paddingHorizontal: Space.md,
    paddingVertical: Space.md,
  },
  emptyWeek: {
    fontSize: Type.labelSmall,
    lineHeight: Type.labelSmall * 1.4,
    paddingTop: Space.sm,
  },
});
