import { useEffect, useMemo, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
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
import { EmptyState } from '@/components/ui/states';
import { useInteraction } from '@/components/ui/interaction';
import {
  Elevation,
  Fonts,
  Radius,
  Space,
  Type,
  type ThemeColors,
} from '@/constants/tokens';
import { addDays, todayISO } from '@/domain/date';
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

/** One text line inside a block; the visibility maths below mirrors the styles. */
const BLOCK_LINE_HEIGHT = 14;
const BLOCK_GAP = 1;

const HOUR_MARKS = Array.from({ length: HOURS + 1 }, (_, index) => START_HOUR + index);
const SLOT_MARKS = Array.from({ length: SLOT_COUNT + 1 }, (_, index) => index);

type Occurrence = {
  event: ScheduleEventRead;
  start: number;
  end: number;
};

type Block = Occurrence & {
  lane: number;
  lanes: number;
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

function minutesNow(now: Date): number {
  return now.getHours() * 60 + now.getMinutes();
}

function clockLabel(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
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
function toOccurrence(event: ScheduleEventRead): Occurrence | null {
  const start = startMinutes(event);
  let end = endMinutes(event);
  // A later-looking end means the course crosses midnight.
  if (end < start) end = DAY_END;
  if (end === start) return null;
  if (end <= DAY_START || start >= DAY_END) return null;
  const clippedStart = Math.max(start, DAY_START);
  const clippedEnd = Math.min(end, DAY_END);
  if (clippedEnd <= clippedStart) return null;
  return { event, start: clippedStart, end: clippedEnd };
}

/**
 * Greedy lane assignment inside each transitive overlap cluster. Touching
 * endpoints do not overlap, so back-to-back courses keep the full column.
 */
function layoutDay(items: Occurrence[]): Block[] {
  const sorted = [...items].sort(
    (a, b) => a.start - b.start || a.end - b.end || a.event.id - b.event.id,
  );
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
    // space so two back-to-back 15-minute events become lanes, not a cover-up.
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

function kindPalette(kind: string, colors: ThemeColors) {
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

export function CourseTimetable({
  events,
  weekStart,
  onSelect,
  onImport,
}: {
  events: ScheduleEventRead[];
  /** Monday of the visible week. */
  weekStart: string;
  onSelect: (event: ScheduleEventRead) => void;
  onImport?: () => void;
}) {
  const { colors } = useTheme();
  const [availableWidth, setAvailableWidth] = useState(0);
  // Re-read the clock once a minute so the now-line tracks the time axis.
  const [nowMinutes, setNowMinutes] = useState(() => minutesNow(new Date()));

  useEffect(() => {
    const timer = setInterval(() => setNowMinutes(minutesNow(new Date())), 60_000);
    return () => clearInterval(timer);
  }, []);

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, index) => addDays(weekStart, index)),
    [weekStart],
  );

  const dayBlocks = useMemo(
    () =>
      days.map((day) => {
        const items: Occurrence[] = [];
        events.forEach((event) => {
          if (!occursOn(event, day)) return;
          const occurrence = toOccurrence(event);
          if (occurrence) items.push(occurrence);
        });
        return layoutDay(items);
      }),
    [days, events],
  );

  const hasContent = dayBlocks.some((blocks) => blocks.length > 0);
  const today = todayISO();
  const todayIndex = days.indexOf(today);
  const showNow = todayIndex >= 0 && nowMinutes >= DAY_START && nowMinutes <= DAY_END;

  // A day with three overlapping courses gets a wider column instead of three
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

  if (!hasContent) {
    return (
      <EmptyState
        title={
          events.length > 0 ? '这一周没有 06:00–24:00 的日程' : '这一周没有固定日程'
        }
        body={
          events.length > 0
            ? '已导入的日程不在这个时间范围内；切换周或检查导入文件里的时间。'
            : '导入 .csv / .xlsx 课程表后，这里会显示每周的课程、考试和固定占用。'
        }
        actionLabel={onImport ? '导入课程表' : undefined}
        actionIcon="calendar"
        onAction={onImport}
      />
    );
  }

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
                  <EventBlock
                    key={`${block.event.id}-${day}-${block.lane}`}
                    block={block}
                    day={day}
                    dayWidth={dayWidth}
                    onPress={() => onSelect(block.event)}
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

function EventBlock({
  block,
  day,
  dayWidth,
  onPress,
}: {
  block: Block;
  day: string;
  dayWidth: number;
  onPress: () => void;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const { event } = block;

  const palette = kindPalette(event.event_kind, colors);
  const gap = block.lanes > 1 ? LANE_GAP : 0;
  const laneWidth = (dayWidth - BLOCK_INSET * 2 - gap * (block.lanes - 1)) / block.lanes;
  const left = BLOCK_INSET + block.lane * (laneWidth + gap);
  const top = ((block.start - DAY_START) / 60) * HOUR_HEIGHT + 1;
  const height = Math.max(
    MIN_BLOCK_HEIGHT,
    ((block.end - block.start) / 60) * HOUR_HEIGHT - 2,
  );

  const location = (event.location ?? '').trim();
  const teacher = (event.teacher ?? '').trim();
  const titleSize = laneWidth < 62 ? Type.labelSmall : Type.labelMedium;
  const weekday = WEEKDAY_LABELS[weekdayIndex(day)];

  // Fit the title first, then spend whatever height is left on location and
  // teacher. Blocks are never stretched or snapped to a slot.
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

  const label = `${event.title}，${weekday} ${monthDay(day)}，${eventTimeRange(event)}${
    location ? `，地点 ${location}` : ''
  }${teacher ? `，教师 ${teacher}` : ''}`;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint="点按查看日程详情或删除"
      onPress={onPress}
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
        style={[styles.eventTitle, { color: palette.foreground, fontSize: titleSize }]}>
        {event.title}
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
    </Pressable>
  );
}

const styles = StyleSheet.create({
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
});
