import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { isApiError } from '@/api/client';
import {
  deleteSchedule,
  importSchedules,
  listSchedules,
  type ScheduleUploadFile,
} from '@/api/endpoints';
import type { ScheduleEventRead, ScheduleImportResult } from '@/api/types';
import { addDays, startOfWeek, todayISO } from '@/domain/date';
import { usePlan } from '@/state/plan';

type ScheduleContextValue = {
  events: ScheduleEventRead[];
  /** True while the visible week is being fetched. */
  loading: boolean;
  /** List/refresh failure. Kept separate from mutations so the page stays. */
  error: string | null;
  /** Import/delete failure; dismissible. */
  actionError: string | null;
  clearActionError: () => void;
  showSchedule: boolean;
  setShowSchedule: (show: boolean) => void;
  /** Monday of the visible week (`YYYY-MM-DD`). */
  weekStart: string;
  setWeekStart: (date: string) => void;
  prevWeek: () => void;
  nextWeek: () => void;
  goToThisWeek: () => void;
  refresh: () => Promise<void>;
  importFile: (file: ScheduleUploadFile) => Promise<ScheduleImportResult | null>;
  remove: (id: number) => Promise<boolean>;
  importing: boolean;
  importResult: ScheduleImportResult | null;
  clearImportResult: () => void;
};

const ScheduleContext = createContext<ScheduleContextValue | null>(null);

function messageOf(error: unknown, fallback: string): string {
  return isApiError(error) ? error.message : fallback;
}

/**
 * Timetable state. Events are fetched per visible week (Monday–Sunday) because
 * the backend expands weekly recurrences for the requested range. Waiting for
 * the plan session (`loading === false`) means the bearer token exists before
 * the first schedule call.
 */
export function ScheduleProvider({ children }: { children: React.ReactNode }) {
  const { mode, loading: planLoading } = usePlan();
  const isApi = mode === 'api';

  const [events, setEvents] = useState<ScheduleEventRead[]>([]);
  const [loading, setLoading] = useState(isApi);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showSchedule, setShowSchedule] = useState(false);
  const [weekStart, setWeekStartState] = useState(() => startOfWeek(todayISO()));
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ScheduleImportResult | null>(null);

  const mountedRef = useRef(true);
  const requestSeqRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      requestSeqRef.current += 1;
    };
  }, []);

  const clearActionError = useCallback(() => setActionError(null), []);
  const clearImportResult = useCallback(() => setImportResult(null), []);

  const setWeekStart = useCallback((date: string) => {
    setWeekStartState(startOfWeek(date));
  }, []);

  const prevWeek = useCallback(() => {
    setWeekStartState((current) => addDays(current, -7));
  }, []);

  const nextWeek = useCallback(() => {
    setWeekStartState((current) => addDays(current, 7));
  }, []);

  const goToThisWeek = useCallback(() => {
    setWeekStartState(startOfWeek(todayISO()));
  }, []);

  const refresh = useCallback(async () => {
    if (!isApi) return;
    const seq = requestSeqRef.current + 1;
    requestSeqRef.current = seq;
    setLoading(true);
    try {
      const next = await listSchedules(weekStart, addDays(weekStart, 6));
      if (!mountedRef.current || seq !== requestSeqRef.current) return;
      setEvents(next);
      setError(null);
    } catch (caught) {
      if (!mountedRef.current || seq !== requestSeqRef.current) return;
      setError(messageOf(caught, '课程表加载失败，请稍后重试。'));
    } finally {
      if (mountedRef.current && seq === requestSeqRef.current) setLoading(false);
    }
  }, [isApi, weekStart]);

  useEffect(() => {
    if (!isApi || planLoading) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch the visible week once the session is ready
    void refresh();
  }, [isApi, planLoading, refresh]);

  const importFile = useCallback(
    async (file: ScheduleUploadFile): Promise<ScheduleImportResult | null> => {
      if (!isApi) {
        setActionError('课程表需要连接后端（API）才能导入。');
        return null;
      }
      setImporting(true);
      setActionError(null);
      setImportResult(null);
      try {
        const result = await importSchedules(file);
        if (!mountedRef.current) return result;
        setImportResult(result);
        await refresh();
        return result;
      } catch (caught) {
        if (mountedRef.current) {
          setActionError(messageOf(caught, '导入失败，原有课程表没有被覆盖。'));
        }
        return null;
      } finally {
        if (mountedRef.current) setImporting(false);
      }
    },
    [isApi, refresh],
  );

  const remove = useCallback(
    async (id: number): Promise<boolean> => {
      if (!isApi) {
        setActionError('课程表需要连接后端（API）才能删除。');
        return false;
      }
      setActionError(null);
      try {
        await deleteSchedule(id);
        if (!mountedRef.current) return true;
        setEvents((current) => current.filter((event) => event.id !== id));
        await refresh();
        return true;
      } catch (caught) {
        if (mountedRef.current) {
          setActionError(messageOf(caught, '删除失败，请稍后再试。'));
        }
        return false;
      }
    },
    [isApi, refresh],
  );

  const value = useMemo<ScheduleContextValue>(
    () => ({
      events,
      loading,
      error,
      actionError,
      clearActionError,
      showSchedule,
      setShowSchedule,
      weekStart,
      setWeekStart,
      prevWeek,
      nextWeek,
      goToThisWeek,
      refresh,
      importFile,
      remove,
      importing,
      importResult,
      clearImportResult,
    }),
    [
      events,
      loading,
      error,
      actionError,
      clearActionError,
      showSchedule,
      weekStart,
      setWeekStart,
      prevWeek,
      nextWeek,
      goToThisWeek,
      refresh,
      importFile,
      remove,
      importing,
      importResult,
      clearImportResult,
    ],
  );

  return <ScheduleContext.Provider value={value}>{children}</ScheduleContext.Provider>;
}

export function useSchedule(): ScheduleContextValue {
  const context = useContext(ScheduleContext);
  if (!context) throw new Error('useSchedule must be used inside <ScheduleProvider>');
  return context;
}
