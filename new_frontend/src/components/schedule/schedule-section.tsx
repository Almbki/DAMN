import { File as NativeFile } from 'expo-file-system';
import * as DocumentPicker from 'expo-document-picker';
import type { DocumentPickerAsset } from 'expo-document-picker';
import { useCallback, useState } from 'react';
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';

import type { ScheduleUploadFile } from '@/api/endpoints';
import type { ScheduleEventRead, ScheduleImportResult } from '@/api/types';
import { CourseTimetable } from '@/components/schedule/course-timetable';
import { formatEventWhen, formatWeekRange } from '@/components/schedule/format';
import { Button, IconButton } from '@/components/ui/button';
import { FilterChip } from '@/components/ui/chip';
import { Dialog } from '@/components/ui/dialog';
import { InlineNotice, LoadingState } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { startOfWeek, todayISO } from '@/domain/date';
import { useSchedule } from '@/state/schedule';
import { useTheme } from '@/state/theme';

const MAX_BYTES = 2 * 1024 * 1024;

const PICK_TYPES = [
  'text/csv',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
];

function mimeForName(name: string): string {
  const lower = name.toLowerCase();
  if (lower.endsWith('.csv')) return 'text/csv';
  if (lower.endsWith('.xlsx')) {
    return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
  }
  return 'application/octet-stream';
}

/**
 * Turn a picked asset into something `expo/fetch` can serialise.
 *
 * Web has a real DOM `File`; native's `DocumentPickerAsset.uri` is not enough
 * for `expo/fetch`, so read the cached copy into a `Blob` and attach the
 * original filename. The backend caps the file at 2 MB, so this stays small.
 */
async function buildUploadFile(asset: DocumentPickerAsset): Promise<ScheduleUploadFile> {
  const name = asset.name || 'timetable.csv';
  const mimeType = asset.mimeType || mimeForName(name);

  if (asset.file) {
    return { uri: asset.uri, name, mimeType, file: asset.file };
  }

  if (Platform.OS !== 'web') {
    const nativeFile = new NativeFile(asset.uri);
    const buffer = await nativeFile.arrayBuffer();
    return {
      uri: asset.uri,
      name,
      mimeType,
      file: new Blob([buffer], { type: mimeType }),
    };
  }

  // Rare web fallback: the picker returned a base64/blob URI without `file`.
  const response = await fetch(asset.uri);
  const blob = await response.blob();
  return { uri: asset.uri, name, mimeType, file: blob };
}

export function ScheduleSection({
  onOverlayChange,
}: {
  /** Lets the todo screen pause its keyboard shortcuts while a dialog is open. */
  onOverlayChange?: (open: boolean) => void;
}) {
  const { colors } = useTheme();
  const {
    events,
    loading,
    error,
    actionError,
    clearActionError,
    showSchedule,
    setShowSchedule,
    weekStart,
    prevWeek,
    nextWeek,
    goToThisWeek,
    refresh,
    importFile,
    remove,
    importing,
    importResult,
    clearImportResult,
  } = useSchedule();

  const [selected, setSelected] = useState<ScheduleEventRead | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ScheduleEventRead | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [pickError, setPickError] = useState<string | null>(null);

  const isCurrentWeek = weekStart === startOfWeek(todayISO());

  const openDetail = useCallback(
    (event: ScheduleEventRead) => {
      setSelected(event);
      onOverlayChange?.(true);
    },
    [onOverlayChange],
  );

  const closeDetail = useCallback(() => {
    setSelected(null);
    onOverlayChange?.(false);
  }, [onOverlayChange]);

  const requestDelete = useCallback(() => {
    if (!selected) return;
    setDeleteTarget(selected);
    setSelected(null);
    // Still an overlay: the confirmation dialog replaces the detail dialog.
  }, [selected]);

  const cancelDelete = useCallback(() => {
    setDeleteTarget(null);
    onOverlayChange?.(false);
  }, [onOverlayChange]);

  const confirmDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    await remove(deleteTarget.id);
    setDeleting(false);
    setDeleteTarget(null);
    onOverlayChange?.(false);
  }, [deleteTarget, remove, onOverlayChange]);

  const pickAndImport = useCallback(async () => {
    if (importing) return;
    setPickError(null);
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: PICK_TYPES,
        copyToCacheDirectory: true,
        multiple: false,
        // Web: prefer the DOM File over a base64 copy of the whole workbook.
        base64: false,
      });
      if (result.canceled) return;

      const asset = result.assets?.[0];
      if (!asset) return;

      const lower = (asset.name || '').toLowerCase();
      if (lower.endsWith('.xls') && !lower.endsWith('.xlsx')) {
        setPickError('不支持 .xls。请先在 Excel 里另存为 .xlsx，再导入。');
        return;
      }
      if (!lower.endsWith('.csv') && !lower.endsWith('.xlsx')) {
        setPickError('只支持 .csv 或 .xlsx 文件。');
        return;
      }
      if (asset.size != null && asset.size > MAX_BYTES) {
        setPickError('文件超过 2MB。请拆分课程表后再导入。');
        return;
      }

      const file = await buildUploadFile(asset);
      await importFile(file);
    } catch (caught) {
      setPickError(
        caught instanceof Error
          ? `读取文件失败：${caught.message}`
          : '读取文件失败，请重新选择。',
      );
    }
  }, [importFile, importing]);

  return (
    <>
      <Surface level="level1" radius="lg" tone="low" contentStyle={styles.panel}>
        <View style={styles.headerRow}>
          <View style={styles.headerCopy}>
            <Text accessibilityRole="header" style={[styles.title, { color: colors.ink }]}>
              课程表 / 日程
            </Text>
            <Text style={[styles.subtitle, { color: colors.inkMuted }]}>
              导入固定课程；生成或重排计划时会自动避开这些时间。
            </Text>
          </View>

          <View style={styles.headerActions}>
            <FilterChip
              label={showSchedule ? '收起' : '展开'}
              selected={showSchedule}
              count={events.length}
              onPress={() => setShowSchedule(!showSchedule)}
            />
            <Button
              label={importing ? '导入中…' : '导入课程表'}
              icon="plus"
              variant="tonal"
              disabled={importing}
              onPress={() => {
                void pickAndImport();
              }}
            />
          </View>
        </View>

        <View
          style={[
            styles.weekRow,
            {
              borderTopColor: colors.outlineVariant,
              borderBottomColor: colors.outlineVariant,
            },
          ]}>
          <IconButton name="arrowLeft" label="上一周" onPress={prevWeek} />
          <View style={styles.weekCenter}>
            <Text numberOfLines={1} style={[styles.weekRange, { color: colors.ink }]}>
              {formatWeekRange(weekStart)}
            </Text>
            <View style={styles.weekMeta}>
              {isCurrentWeek ? (
                <Text style={[styles.weekTag, { color: colors.primary }]}>本周</Text>
              ) : (
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="回到本周"
                  onPress={goToThisWeek}
                  hitSlop={8}
                  style={styles.weekLink}>
                  <Text style={[styles.weekLinkText, { color: colors.primary }]}>回到本周</Text>
                </Pressable>
              )}
              {loading ? (
                <Text style={[styles.updating, { color: colors.inkMuted }]}>更新中…</Text>
              ) : null}
            </View>
          </View>
          <IconButton name="arrowRight" label="下一周" onPress={nextWeek} />
        </View>

        <Text style={[styles.help, { color: colors.inkMuted }]}>
          支持 .csv / .xlsx（不支持 .xls），单文件 ≤ 2MB / 1000 行。无法识别的行会跳过，并在导入结果里列出。
        </Text>

        {error ? (
          <InlineNotice
            message={error}
            actionLabel="重试"
            onAction={() => {
              void refresh();
            }}
          />
        ) : null}

        {actionError ? (
          <InlineNotice message={actionError} onDismiss={clearActionError} />
        ) : null}

        {pickError ? (
          <InlineNotice message={pickError} onDismiss={() => setPickError(null)} />
        ) : null}

        {importResult ? (
          <ImportResultPanel result={importResult} onDismiss={clearImportResult} />
        ) : null}

        {showSchedule ? (
          loading && events.length === 0 ? (
            <View style={styles.loading}>
              <LoadingState label="正在读取课程表…" />
            </View>
          ) : (
            <CourseTimetable
              events={events}
              weekStart={weekStart}
              onSelect={openDetail}
              onImport={() => {
                void pickAndImport();
              }}
            />
          )
        ) : null}
      </Surface>

      <Dialog
        visible={selected != null}
        title={selected?.title ?? ''}
        onRequestClose={closeDetail}
        actions={[
          { label: '关闭', variant: 'text', onPress: closeDetail },
          { label: '删除', variant: 'tonal', onPress: requestDelete },
        ]}>
        {selected ? (
          <View style={styles.detail}>
            <DetailRow label="时间" value={formatEventWhen(selected)} />
            {selected.location ? <DetailRow label="地点" value={selected.location} /> : null}
            {selected.teacher ? <DetailRow label="教师" value={selected.teacher} /> : null}
          </View>
        ) : null}
      </Dialog>

      <Dialog
        visible={deleteTarget != null}
        title="删除这个日程？"
        description="每周重复的课程会整条删除。删除后，下次生成或重排计划时不会再避开这段时间；已经生成的任务不会自动改动。"
        onRequestClose={cancelDelete}
        actions={[
          {
            label: '取消',
            variant: 'text',
            disabled: deleting,
            onPress: cancelDelete,
          },
          {
            label: deleting ? '删除中…' : '删除',
            variant: 'filled',
            disabled: deleting,
            onPress: () => {
              void confirmDelete();
            },
          },
        ]}>
        {deleteTarget ? (
          <View
            style={[
              styles.deleteSummary,
              {
                borderColor: colors.outlineVariant,
                backgroundColor: colors.surfaceContainerLow,
              },
            ]}>
            <Text style={[styles.deleteTitle, { color: colors.ink }]} numberOfLines={2}>
              {deleteTarget.title}
            </Text>
            <Text style={[styles.deleteMeta, { color: colors.inkMuted }]}>
              {formatEventWhen(deleteTarget)}
            </Text>
          </View>
        ) : null}
      </Dialog>
    </>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.detailRow}>
      <Text style={[styles.detailLabel, { color: colors.inkMuted }]}>{label}</Text>
      <Text style={[styles.detailValue, { color: colors.ink }]}>{value}</Text>
    </View>
  );
}

function ImportResultPanel({
  result,
  onDismiss,
}: {
  result: ScheduleImportResult;
  onDismiss: () => void;
}) {
  const { colors } = useTheme();
  const empty =
    result.imported === 0 &&
    result.updated === 0 &&
    result.warnings.length === 0 &&
    result.conflicts.length === 0;

  return (
    <View
      accessibilityLiveRegion="polite"
      style={[
        styles.result,
        {
          borderColor: colors.outlineVariant,
          backgroundColor: colors.surfaceContainerLowest,
        },
      ]}>
      <View style={styles.resultHeader}>
        <Text style={[styles.resultTitle, { color: colors.ink }]}>导入结果</Text>
        <IconButton name="close" label="关闭导入结果" onPress={onDismiss} />
      </View>

      <View style={styles.resultCounts}>
        <ResultCount label="新增" value={result.imported} />
        <ResultCount label="更新" value={result.updated} />
        <ResultCount label="跳过" value={result.skipped} />
      </View>

      {result.warnings.length > 0 ? (
        <ResultList
          title={`警告 · ${result.warnings.length}`}
          items={result.warnings}
          tone={colors.warning}
        />
      ) : null}

      {result.conflicts.length > 0 ? (
        <ResultList
          title={`时间冲突 · ${result.conflicts.length}`}
          items={result.conflicts}
          tone={colors.error}
        />
      ) : null}

      {empty ? (
        <Text style={[styles.resultEmpty, { color: colors.inkMuted }]}>
          文件里没有可导入的行，检查一下表头和日期/时间格式。
        </Text>
      ) : null}
    </View>
  );
}

function ResultCount({ label, value }: { label: string; value: number }) {
  const { colors } = useTheme();
  return (
    <View style={styles.count}>
      <Text style={[styles.countValue, { color: colors.ink }]}>{value}</Text>
      <Text style={[styles.countLabel, { color: colors.inkMuted }]}>{label}</Text>
    </View>
  );
}

function ResultList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: string;
}) {
  const { colors } = useTheme();
  const shown = items.slice(0, 5);
  const rest = items.length - shown.length;

  return (
    <View style={styles.resultList}>
      <Text style={[styles.resultListTitle, { color: tone }]}>{title}</Text>
      {shown.map((item, index) => (
        <Text
          key={`${index}-${item}`}
          style={[styles.resultItem, { color: colors.inkMuted }]}>
          • {item}
        </Text>
      ))}
      {rest > 0 ? (
        <Text style={[styles.resultItem, { color: colors.inkFaint }]}>还有 {rest} 条…</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    padding: Space.lg,
    gap: Space.md,
  },
  headerRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  headerCopy: {
    flexGrow: 1,
    flexBasis: 240,
    minWidth: 0,
    gap: Space.xs,
  },
  title: {
    fontSize: Type.titleLarge,
    fontWeight: '600',
  },
  subtitle: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.normal,
  },
  headerActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: Space.sm,
  },
  weekRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    paddingVertical: Space.xs,
  },
  weekCenter: {
    flex: 1,
    minWidth: 0,
    alignItems: 'center',
    gap: 2,
  },
  weekRange: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelLarge,
    textAlign: 'center',
  },
  weekMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  weekTag: {
    fontSize: Type.labelSmall,
    fontWeight: '600',
  },
  weekLink: {
    minHeight: 24,
    justifyContent: 'center',
  },
  weekLinkText: {
    fontSize: Type.labelSmall,
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  updating: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelSmall,
  },
  help: {
    fontSize: Type.labelSmall,
    lineHeight: Type.labelSmall * Line.relaxed,
  },
  loading: {
    paddingVertical: Space.lg,
  },
  result: {
    borderWidth: 1,
    borderRadius: Radius.md,
    padding: Space.md,
    gap: Space.sm,
  },
  resultHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  resultTitle: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
  },
  resultCounts: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.lg,
  },
  count: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: Space.xs,
  },
  countValue: {
    fontFamily: Fonts.mono,
    fontSize: Type.titleLarge,
  },
  countLabel: {
    fontSize: Type.labelMedium,
  },
  resultList: {
    gap: 2,
  },
  resultListTitle: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  resultItem: {
    fontSize: Type.labelSmall,
    lineHeight: Type.labelSmall * Line.normal,
  },
  resultEmpty: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.normal,
  },
  detail: {
    gap: Space.lg,
  },
  detailRow: {
    gap: Space.xs,
  },
  detailLabel: {
    fontSize: Type.labelSmall,
    fontWeight: '600',
    letterSpacing: 0.4,
  },
  detailValue: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.normal,
  },
  deleteSummary: {
    borderWidth: 1,
    borderRadius: Radius.md,
    padding: Space.md,
    gap: Space.xs,
  },
  deleteTitle: {
    fontSize: Type.bodyLarge,
    fontWeight: '600',
    lineHeight: Type.bodyLarge * Line.normal,
  },
  deleteMeta: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.normal,
  },
});
