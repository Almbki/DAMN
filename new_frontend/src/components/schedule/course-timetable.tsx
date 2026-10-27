import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type GestureResponderEvent,
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
  Radius,
  Space,
  Type,
  type ThemeColors,
} from '@/constants/tokens';
import { addDays, todayISO } from '@/domain/date';
import type { Goal } from '@/domain/goal';
import {
  dropTargetFromPosition,
  minutesToTime,
  timeToMinutes,
  type DropTarget,
} from '@/domain/schedule-drag';
import { isBacklog, isClosed, type Task } from '@/domain/task';
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
const LONG_PRESS_MS = 270;
const DRAG_SLOP = 8;

type MoveResult = { ok: boolean; message: string | null };
type WindowRect = { x: number; y: number; width: number; height: number };

type DragState = {
  task: Task;
  pageX: number;
  pageY: number;
  target: DropTarget | null;
  overTray: boolean;
};

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
    if (isBacklog(task)) return false;
    const day = taskDay(task);
    return day != null && day >= weekStart && day <= weekEnd;
  });
}

/**
 * Planned tasks use `startTime` (or `dueTime`), then `endTime`, then the
 * estimate, then a 30-minute default. Like events, they are clipped to the
 * 06:00–24:00 grid; anything without a placeable clock time is not drawn.
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
  backlogTasks,
  goals,
  weekStart,
  canEdit = true,
  onSelect,
  onSelectTask,
  onMoveTask,
  onMoveToBacklog,
}: {
  events: ScheduleEventRead[];
  tasks: Task[];
  backlogTasks: Task[];
  goals: Goal[];
  /** Monday of the visible week. */
  weekStart: string;
  canEdit?: boolean;
  onSelect: (event: ScheduleEventRead) => void;
  onSelectTask: (task: Task) => void;
  onMoveTask: (taskId: number, targetDate: string, targetStart: string) => Promise<MoveResult>;
  onMoveToBacklog: (taskId: number) => Promise<MoveResult>;
}) {
  const { colors } = useTheme();

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, index) => addDays(weekStart, index)),
    [weekStart],
  );

  const weekTasks = useMemo(() => tasksForWeek(tasks, weekStart), [tasks, weekStart]);
  const dayBlocks = useMemo(
    () => days.map((day) => layoutDay(buildDayOccurrences(events, weekTasks, day))),
    [days, events, weekTasks],
  );

  const [drag, setDrag] = useState<DragState | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const gridBodyRef = useRef<View>(null);
  const trayRef = useRef<View>(null);
  const gridRectRef = useRef<WindowRect | null>(null);
  const trayRectRef = useRef<WindowRect | null>(null);
  const [moving, setMoving] = useState(false);

  const applyPointer = useCallback(
    (pageX: number, pageY: number) => {
      const current = dragRef.current;
      if (!current) return;

      const tray = trayRectRef.current;
      const overTray =
        tray != null &&
        pageX >= tray.x &&
        pageX <= tray.x + tray.width &&
        pageY >= tray.y &&
        pageY <= tray.y + tray.height;

      let target: DropTarget | null = null;
      const grid = gridRectRef.current;
      if (!overTray && grid != null && days.length > 0 && grid.width > 0) {
        target = dropTargetFromPosition(
          { x: pageX - grid.x, y: pageY - grid.y },
          {
            days,
            // The measured node is the first day column: its width is one day,
            // and its x already includes any horizontal scroll offset.
            dayWidth: grid.width,
            hourHeight: HOUR_HEIGHT,
            dayStart: DAY_START,
            dayEnd: DAY_END,
            slotMinutes: SLOT_MINUTES,
          },
        );
      }

      const next = { ...current, pageX, pageY, target, overTray };
      dragRef.current = next;
      setDrag(next);
    },
    [days],
  );

  const beginDrag = useCallback(
    (task: Task, pageX: number, pageY: number) => {
      if (!canEdit || moving || isClosed(task)) return;
      const next: DragState = { task, pageX, pageY, target: null, overTray: false };
      dragRef.current = next;
      setDrag(next);
      gridRectRef.current = null;
      trayRectRef.current = null;

      const refresh = () => {
        const current = dragRef.current;
        if (current) applyPointer(current.pageX, current.pageY);
      };
      gridBodyRef.current?.measureInWindow((x, y, width, height) => {
        gridRectRef.current = { x, y, width, height };
        refresh();
      });
      trayRef.current?.measureInWindow((x, y, width, height) => {
        trayRectRef.current = { x, y, width, height };
        refresh();
      });
    },
    [applyPointer, canEdit, moving],
  );

  const moveDrag = useCallback(
    (pageX: number, pageY: number) => {
      if (!dragRef.current) return;
      applyPointer(pageX, pageY);
    },
    [applyPointer],
  );

  const cancelDrag = useCallback(() => {
    dragRef.current = null;
    setDrag(null);
  }, []);

  const runMove = useCallback(async (action: () => Promise<MoveResult>) => {
    setMoving(true);
    try {
      await action();
    } catch {
      // The provider surfaces the mapped scheduling reason via actionError.
    } finally {
      setMoving(false);
    }
  }, []);

  const endDrag = useCallback(
    (pageX: number, pageY: number) => {
      if (!dragRef.current) return;
      applyPointer(pageX, pageY);
      const final = dragRef.current;
      dragRef.current = null;
      setDrag(null);
      if (!final) return;

      if (final.overTray) {
        if (final.task.backlog !== true) {
          void runMove(() => onMoveToBacklog(final.task.id));
        }
        return;
      }
      const target = final.target;
      if (!target) return;
      const currentStart = final.task.startTime ?? final.task.dueTime;
      if (final.task.dueDate === target.date && currentStart === target.start) return;
      void runMove(() => onMoveTask(final.task.id, target.date, target.start));
    },
    [applyPointer, onMoveTask, onMoveToBacklog, runMove],
  );

  const draggingTaskId = drag?.task.id ?? null;
  const dragTargetIndex = drag?.target ? days.indexOf(drag.target.date) : -1;
  const dragStartMinutes = drag?.target ? timeToMinutes(drag.target.start) : null;
  const dragActive = drag != null;
  const hasPlacedContent = dayBlocks.some((blocks) => blocks.length > 0);

  return (
    <View style={styles.root}>
      <DesktopTimetable
        days={days}
        dayBlocks={dayBlocks}
        onSelectEvent={onSelect}
        onSelectTask={onSelectTask}
        bodyRef={gridBodyRef}
        canDrag={canEdit && !moving}
        dragActive={dragActive}
        draggingTaskId={draggingTaskId}
        dragTargetIndex={dragTargetIndex}
        dragStartMinutes={dragStartMinutes}
        scrollEnabled={!dragActive}
        onDragStart={beginDrag}
        onDragMove={moveDrag}
        onDragEnd={endDrag}
        onDragCancel={cancelDrag}
      />
      {!hasPlacedContent && backlogTasks.length === 0 ? (
        <Text style={[styles.emptyWeek, { color: colors.inkMuted }]}>
          本周暂无课程或任务安排。
        </Text>
      ) : null}

      <BacklogTray
        trayRef={trayRef}
        tasks={backlogTasks}
        goals={goals}
        dragActive={dragActive}
        active={drag?.overTray === true}
        draggingTaskId={draggingTaskId}
        moving={moving}
        canDrag={canEdit}
        onSelectTask={onSelectTask}
        onDragStart={beginDrag}
        onDragMove={moveDrag}
        onDragEnd={endDrag}
        onDragCancel={cancelDrag}
      />
    </View>
  );
}

/**
 * Long-press gesture shared by grid cards and tray rows.
 *
 * It claims the responder on touch-down so a held press can become a drag;
 * before the timer fires it gives the responder back, which keeps the parent
 * scroller usable. A release without an active drag stays a normal tap.
 */
function useTaskDrag({
  dragDisabled,
  onTap,
  onDragStart,
  onDragMove,
  onDragEnd,
  onDragCancel,
}: {
  dragDisabled: boolean;
  onTap: () => void;
  onDragStart: (pageX: number, pageY: number) => void;
  onDragMove: (pageX: number, pageY: number) => void;
  onDragEnd: (pageX: number, pageY: number) => void;
  onDragCancel: () => void;
}) {
  const [pressed, setPressed] = useState(false);
  const [dragging, setDragging] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const originRef = useRef<{ x: number; y: number } | null>(null);
  const lastRef = useRef<{ x: number; y: number } | null>(null);
  const activeRef = useRef(false);

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    [],
  );

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const point = (event: GestureResponderEvent) => ({
    x: event.nativeEvent.pageX,
    y: event.nativeEvent.pageY,
  });

  const grant = (event: GestureResponderEvent) => {
    const start = point(event);
    originRef.current = start;
    lastRef.current = start;
    setPressed(true);
    if (dragDisabled) return;
    timerRef.current = setTimeout(() => {
      timerRef.current = null;
      activeRef.current = true;
      setDragging(true);
      onDragStart(start.x, start.y);
    }, LONG_PRESS_MS);
  };

  const move = (event: GestureResponderEvent) => {
    const next = point(event);
    lastRef.current = next;
    if (activeRef.current) {
      onDragMove(next.x, next.y);
      return;
    }
    const origin = originRef.current;
    if (origin) {
      const dx = next.x - origin.x;
      const dy = next.y - origin.y;
      if (Math.hypot(dx, dy) > DRAG_SLOP) {
        // The user is scrolling, not holding: do not treat the release as a tap.
        originRef.current = null;
        clearTimer();
      }
    }
  };

  const release = (event: GestureResponderEvent) => {
    const final = lastRef.current ?? point(event);
    clearTimer();
    setPressed(false);
    const wasDragging = activeRef.current;
    activeRef.current = false;
    setDragging(false);

    if (wasDragging) {
      onDragEnd(final.x, final.y);
    } else if (originRef.current) {
      onTap();
    }
    originRef.current = null;
    lastRef.current = null;
  };

  const terminate = () => {
    clearTimer();
    setPressed(false);
    const wasDragging = activeRef.current;
    activeRef.current = false;
    setDragging(false);
    originRef.current = null;
    lastRef.current = null;
    if (wasDragging) onDragCancel();
  };

  return {
    pressed,
    dragging,
    responderProps: {
      onStartShouldSetResponder: () => true,
      onResponderGrant: grant,
      onResponderMove: move,
      onResponderRelease: release,
      onResponderTerminate: terminate,
      onResponderTerminationRequest: () => !activeRef.current,
    },
  };
}

function BacklogTray({
  trayRef,
  tasks,
  goals,
  dragActive,
  active,
  draggingTaskId,
  moving,
  canDrag,
  onSelectTask,
  onDragStart,
  onDragMove,
  onDragEnd,
  onDragCancel,
}: {
  trayRef: React.RefObject<View | null>;
  tasks: Task[];
  goals: Goal[];
  dragActive: boolean;
  active: boolean;
  draggingTaskId: number | null;
  moving: boolean;
  canDrag: boolean;
  onSelectTask: (task: Task) => void;
  onDragStart: (task: Task, pageX: number, pageY: number) => void;
  onDragMove: (pageX: number, pageY: number) => void;
  onDragEnd: (pageX: number, pageY: number) => void;
  onDragCancel: () => void;
}) {
  const { colors } = useTheme();
  const goalById = useMemo(() => new Map(goals.map((goal) => [goal.id, goal])), [goals]);
  const ordered = useMemo(
    () => [...tasks].sort((a, b) => a.order - b.order || a.id - b.id),
    [tasks],
  );

  const hint = moving
    ? '正在更新…'
    : active
      ? '松手放入任务池'
      : dragActive
        ? '拖到这里可以移出时间表'
        : canDrag
          ? '长按卡片拖动到时间表'
          : '当前计划不可编辑';

  return (
    <View
      ref={trayRef}
      style={[
        styles.backlog,
        {
          borderColor: active ? colors.primary : colors.outlineVariant,
          borderStyle: dragActive ? 'dashed' : 'solid',
          backgroundColor: active ? colors.primaryContainer : colors.surfaceContainerLow,
        },
      ]}>
      <View style={styles.backlogHeader}>
        <View style={styles.backlogHeading}>
          <Text
            style={[
              styles.backlogTitle,
              { color: active ? colors.onPrimaryContainer : colors.ink },
            ]}>
            任务池
          </Text>
          <Text
            style={[
              styles.backlogCount,
              { color: active ? colors.onPrimaryContainer : colors.inkMuted },
            ]}>
            {ordered.length} 件
          </Text>
        </View>
        <Text
          style={[
            styles.backlogHint,
            { color: active ? colors.onPrimaryContainer : colors.inkFaint },
          ]}>
          {hint}
        </Text>
      </View>

      {ordered.length === 0 ? (
        <Text
          style={[
            styles.backlogEmpty,
            { color: active ? colors.onPrimaryContainer : colors.inkFaint },
          ]}>
          任务池是空的。暂时不想排时间的任务，可以从任务详情放进来。
        </Text>
      ) : (
        ordered.map((task, index) => {
          const goal = task.goalId == null ? null : (goalById.get(task.goalId) ?? null);
          return (
            <BacklogRow
              key={task.id}
              task={task}
              goal={goal}
              divider={index > 0}
              dragging={draggingTaskId === task.id}
              dragDisabled={!canDrag || moving}
              onSelectTask={onSelectTask}
              onDragStart={onDragStart}
              onDragMove={onDragMove}
              onDragEnd={onDragEnd}
              onDragCancel={onDragCancel}
            />
          );
        })
      )}
    </View>
  );
}

function BacklogRow({
  task,
  goal,
  divider,
  dragging,
  dragDisabled,
  onSelectTask,
  onDragStart,
  onDragMove,
  onDragEnd,
  onDragCancel,
}: {
  task: Task;
  goal: Goal | null;
  divider: boolean;
  dragging: boolean;
  dragDisabled: boolean;
  onSelectTask: (task: Task) => void;
  onDragStart: (task: Task, pageX: number, pageY: number) => void;
  onDragMove: (pageX: number, pageY: number) => void;
  onDragEnd: (pageX: number, pageY: number) => void;
  onDragCancel: () => void;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const gesture = useTaskDrag({
    dragDisabled,
    onTap: () => onSelectTask(task),
    onDragStart: (pageX, pageY) => onDragStart(task, pageX, pageY),
    onDragMove,
    onDragEnd,
    onDragCancel,
  });

  const duration = task.estimatedMinutes ?? task.predictedDuration;
  const meta = [
    duration != null ? `${duration} 分钟` : '时长未设置',
    goal?.title ?? '未归入目标',
    goal?.deadline ? `截止 ${monthDay(goal.deadline)}` : null,
    task.overdue === true ? '原已逾期' : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <View
      {...gesture.responderProps}
      accessible
      accessibilityRole="button"
      accessibilityLabel={`任务池：${task.title}，${meta}`}
      accessibilityHint="点按查看任务详情，长按拖动到时间表"
      focusable
      {...handlers}
      style={[
        styles.backlogRow,
        divider
          ? { borderTopColor: colors.outlineVariant, borderTopWidth: 1 }
          : null,
        {
          opacity: gesture.dragging || dragging ? 0.35 : gesture.pressed ? 0.72 : hovered ? 0.94 : 1,
          boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      <Text numberOfLines={2} style={[styles.backlogTask, { color: colors.ink }]}>
        {task.title}
      </Text>
      <Text style={[styles.backlogMeta, { color: colors.inkMuted }]}>{meta}</Text>
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
  bodyRef,
  canDrag,
  dragActive,
  draggingTaskId,
  dragTargetIndex,
  dragStartMinutes,
  scrollEnabled,
  onDragStart,
  onDragMove,
  onDragEnd,
  onDragCancel,
}: {
  days: string[];
  dayBlocks: Block[][];
  onSelectEvent: (event: ScheduleEventRead) => void;
  onSelectTask: (task: Task) => void;
  bodyRef: React.RefObject<View | null>;
  canDrag: boolean;
  dragActive: boolean;
  draggingTaskId: number | null;
  dragTargetIndex: number;
  dragStartMinutes: number | null;
  scrollEnabled: boolean;
  onDragStart: (task: Task, pageX: number, pageY: number) => void;
  onDragMove: (pageX: number, pageY: number) => void;
  onDragEnd: (pageX: number, pageY: number) => void;
  onDragCancel: () => void;
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
        scrollEnabled={scrollEnabled}
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
                       backgroundColor:
                         index === dragTargetIndex ? colors.primaryContainer : 'transparent',
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
                ref={index === 0 ? bodyRef : undefined}
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
                {index === dragTargetIndex ? (
                  <View
                    pointerEvents="none"
                    style={[styles.dropColumn, { backgroundColor: colors.primaryContainer }]}
                  />
                ) : null}
                {dayBlocks[index].map((block) => (
                  <ScheduleBlock
                    key={`${block.kind}-${occurrenceId(block)}-${day}-${block.lane}`}
                    block={block}
                    day={day}
                    dayWidth={dayWidth}
                    canDrag={canDrag}
                    dragging={block.kind === 'task' && draggingTaskId === block.task.id}
                    onSelectEvent={onSelectEvent}
                    onSelectTask={onSelectTask}
                    onDragStart={onDragStart}
                    onDragMove={onDragMove}
                    onDragEnd={onDragEnd}
                    onDragCancel={onDragCancel}
                  />
                ))}
                {index === dragTargetIndex && dragStartMinutes != null ? (
                  <View
                    pointerEvents="none"
                    style={[
                      styles.dropSlot,
                      {
                        top: ((dragStartMinutes - DAY_START) / 60) * HOUR_HEIGHT,
                        height: SLOT_HEIGHT,
                        borderColor: colors.primary,
                        backgroundColor: colors.primaryContainer,
                      },
                    ]}>
                    <Text style={[styles.dropSlotLabel, { color: colors.onPrimaryContainer }]}>
                      {minutesToTime(dragStartMinutes)}
                    </Text>
                  </View>
                ) : null}
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

function ScheduleBlock({
  block,
  day,
  dayWidth,
  canDrag,
  dragging,
  onSelectEvent,
  onSelectTask,
  onDragStart,
  onDragMove,
  onDragEnd,
  onDragCancel,
}: {
  block: Block;
  day: string;
  dayWidth: number;
  canDrag: boolean;
  dragging: boolean;
  onSelectEvent: (event: ScheduleEventRead) => void;
  onSelectTask: (task: Task) => void;
  onDragStart: (task: Task, pageX: number, pageY: number) => void;
  onDragMove: (pageX: number, pageY: number) => void;
  onDragEnd: (pageX: number, pageY: number) => void;
  onDragCancel: () => void;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const isEvent = block.kind === 'event';
  const task = block.kind === 'task' ? block.task : null;
  const palette = isEvent
    ? kindPalette(block.event.event_kind, colors)
    : taskPalette(block.task, colors);
  const done = !isEvent && block.task.done;
  const skipped = !isEvent && block.task.skipped;
  const title = isEvent ? block.event.title : block.task.title;
  const location = isEvent ? (block.event.location ?? '').trim() : '';
  const teacher = isEvent ? (block.event.teacher ?? '').trim() : '';

  const gesture = useTaskDrag({
    dragDisabled: isEvent || !canDrag || (task != null && isClosed(task)),
    onTap: () => {
      if (isEvent) onSelectEvent(block.event);
      else if (task) onSelectTask(task);
    },
    onDragStart: (pageX, pageY) => {
      if (task) onDragStart(task, pageX, pageY);
    },
    onDragMove,
    onDragEnd,
    onDragCancel,
  });

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
    !isEvent && (done || skipped || block.task.estimatedMinutes || block.task.backlog)
      ? [
          done ? '已完成' : skipped ? '已跳过' : '',
          block.task.estimatedMinutes ? `${block.task.estimatedMinutes} 分钟` : '',
          block.task.backlog ? '任务池' : '',
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

  const content = (
    <>
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
    </>
  );

  const blockStyle = {
    top,
    left,
    width: laneWidth,
    height,
    backgroundColor: palette.background,
    borderLeftColor: palette.accent,
  };

  if (isEvent) {
    return (
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        accessibilityHint="点按查看日程详情或删除"
        onPress={() => onSelectEvent(block.event)}
        hitSlop={8}
        focusable
        {...handlers}
        style={({ pressed }) => [
          styles.event,
          blockStyle,
          {
            opacity: pressed ? 0.84 : hovered ? 0.94 : 1,
            boxShadow: focused
              ? `inset 0 0 0 2px ${colors.focusRing}`
              : Elevation.highlight,
          },
        ]}>
        {content}
      </Pressable>
    );
  }

  const active = gesture.dragging || dragging;
  return (
    <View
      {...gesture.responderProps}
      accessible
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint="点按查看任务详情，长按拖动可重新安排"
      focusable
      {...handlers}
      style={[
        styles.event,
        blockStyle,
        {
          opacity: active ? 0.35 : gesture.pressed ? 0.84 : hovered ? 0.94 : 1,
          boxShadow: active
            ? `inset 0 0 0 2px ${colors.primary}`
            : focused
              ? `inset 0 0 0 2px ${colors.focusRing}`
              : Elevation.highlight,
        },
      ]}>
      {content}
    </View>
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
  dropColumn: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    opacity: 0.22,
  },
  dropSlot: {
    position: 'absolute',
    left: BLOCK_INSET,
    right: BLOCK_INSET,
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: Radius.xs,
    paddingHorizontal: 4,
    zIndex: 2,
  },
  dropSlotLabel: {
    fontFamily: Fonts.mono,
    fontSize: Type.micro,
    lineHeight: 12,
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
    userSelect: 'none',
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
  backlog: {
    borderWidth: 1,
    borderRadius: Radius.md,
    overflow: 'hidden',
  },
  backlogHeader: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.md,
    paddingHorizontal: Space.md,
    paddingVertical: Space.sm,
  },
  backlogHeading: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: Space.sm,
  },
  backlogTitle: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
  },
  backlogCount: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelSmall,
  },
  backlogHint: {
    flexGrow: 1,
    flexBasis: 180,
    fontSize: Type.labelSmall,
    lineHeight: Type.labelSmall * 1.4,
    textAlign: 'right',
  },
  backlogEmpty: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * 1.5,
    paddingHorizontal: Space.md,
    paddingBottom: Space.md,
  },
  backlogRow: {
    paddingHorizontal: Space.md,
    paddingVertical: Space.sm,
    gap: 2,
    borderRadius: Radius.sm,
    userSelect: 'none',
  },
  backlogTask: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * 1.4,
  },
  backlogMeta: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelSmall,
    lineHeight: Type.labelSmall * 1.4,
  },
  emptyWeek: {
    fontSize: Type.labelSmall,
    lineHeight: Type.labelSmall * 1.4,
    paddingTop: Space.sm,
  },
});
