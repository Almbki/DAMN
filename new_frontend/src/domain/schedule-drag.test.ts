import { describe, expect, it } from 'vitest';

import {
  addMinutesToTime,
  dropTargetFromPosition,
  minutesToTime,
  snapMinutesToGrid,
  timeToMinutes,
} from '@/domain/schedule-drag';

describe('snapMinutesToGrid', () => {
  const cases: [string, string][] = [
    ['14:00', '14:00'],
    ['14:14', '14:00'],
    ['14:15', '14:30'],
    ['14:16', '14:30'],
    ['14:30', '14:30'],
    ['14:44', '14:30'],
    ['14:46', '15:00'],
  ];

  it.each(cases)('snaps %s half-up to %s', (input, expected) => {
    const minutes = timeToMinutes(input);
    expect(minutes).not.toBeNull();
    expect(minutesToTime(snapMinutesToGrid(minutes ?? 0, 30))).toBe(expected);
  });

  it('does not snap the end of a duration', () => {
    expect(addMinutesToTime('09:30', 75)).toBe('10:45');
  });
});

describe('time conversion', () => {
  it('accepts HH:MM and HH:MM:SS', () => {
    expect(timeToMinutes('09:30')).toBe(570);
    expect(timeToMinutes('09:30:00')).toBe(570);
    expect(timeToMinutes('24:00')).toBe(1440);
    expect(timeToMinutes('nope')).toBeNull();
  });
});

describe('dropTargetFromPosition', () => {
  const days = [
    '2026-10-26',
    '2026-10-27',
    '2026-10-28',
    '2026-10-29',
    '2026-10-30',
    '2026-10-31',
    '2026-11-01',
  ];
  const grid = {
    days,
    dayWidth: 100,
    hourHeight: 48,
    dayStart: 360,
    dayEnd: 1440,
  };
  const yFor = (time: string) => ((timeToMinutes(time) ?? 0) - 360) / 60 * 48;

  it('maps a cross-day drop to a date and snapped start', () => {
    expect(dropTargetFromPosition({ x: 250, y: yFor('14:16') }, grid)).toEqual({
      date: '2026-10-28',
      start: '14:30',
    });
  });

  it('uses the last day at the right edge', () => {
    expect(dropTargetFromPosition({ x: 699, y: yFor('08:00') }, grid)).toEqual({
      date: '2026-11-01',
      start: '08:00',
    });
  });

  it('clamps a late drop to the last 30-minute slot', () => {
    expect(dropTargetFromPosition({ x: 0, y: yFor('23:50') }, grid)?.start).toBe('23:30');
  });

  it('rejects points outside the grid', () => {
    expect(dropTargetFromPosition({ x: -1, y: 10 }, grid)).toBeNull();
    expect(dropTargetFromPosition({ x: 10, y: -1 }, grid)).toBeNull();
    expect(dropTargetFromPosition({ x: 700, y: 10 }, grid)).toBeNull();
  });
});
