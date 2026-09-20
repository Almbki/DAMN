import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { describeApiError } from '@/api/client';
import { API_BASE_URL } from '@/api/config';
import * as endpoints from '@/api/endpoints';
import { formatMonthDay } from '@/api/format';
import { Btn, Card, Field, LevelPicker, MonoInput, MonoText, Screen } from '@/components/mono';
import { MonoSpace } from '@/constants/mono';
import { usePlan } from '@/plan/plan-provider';
import { planStatusLabel } from '@/plan/selectors';
import { useThemeMode, type ThemeMode } from '@/hooks/use-theme-mode';
import { useAuthToken, useSession } from '@/session/session-provider';

/**
 * 设置。
 *
 * 模板里的「模型选择 / 通知频率」后端没有对应字段，**不做假开关**；
 * 这里全部接真实能力：账号资料（`PATCH /users/me`）、外观切换、后端地址、退出登录。
 *
 * 「外观」用三档选择器（浅色 / 深色 / 跟系统），走的是现有的 `ThemeModeProvider`，
 * 和 `?theme=` 覆盖、系统外观是同一条链路，不会破坏原有行为。
 */

const THEME_OPTIONS = ['浅色', '深色', '跟系统'] as const;

function modeToIndex(mode: ThemeMode): number {
  return mode === 'light' ? 0 : mode === 'dark' ? 1 : 2;
}

function indexToMode(index: number): ThemeMode {
  return index === 0 ? 'light' : index === 1 ? 'dark' : 'system';
}

export default function SettingsScreen() {
  const token = useAuthToken();
  const { user, signOut, refreshUser } = useSession();
  const { plan } = usePlan();
  const { mode, setMode } = useThemeMode();

  const [name, setName] = useState(user?.display_name ?? '');
  const [weight, setWeight] = useState(
    user ? String(Math.round(user.execution_weight * 100)) : '50',
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: 'ok' | 'error'; text: string } | null>(null);

  // 用户资料可能在别处被刷新（比如换账号），跟着同步一次
  useEffect(() => {
    setName(user?.display_name ?? '');
    setWeight(user ? String(Math.round(user.execution_weight * 100)) : '50');
  }, [user]);

  const weightNumber = Number(weight);
  const weightOk = Number.isFinite(weightNumber) && weightNumber >= 0 && weightNumber <= 100;

  const save = async () => {
    if (!weightOk) return;
    setBusy(true);
    setMessage(null);
    try {
      await endpoints.updateMe(token, {
        display_name: name.trim() || null,
        execution_weight: weightNumber / 100,
      });
      await refreshUser();
      setMessage({ tone: 'ok', text: '已保存。' });
    } catch (cause) {
      setMessage({ tone: 'error', text: describeApiError(cause) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <Card title="账号">
        <Field label="邮箱">
          <MonoText type="body" color="sub">
            {user?.email ?? '—'}
          </MonoText>
        </Field>
        <Field label="称呼">
          <MonoInput
            value={name}
            onChangeText={setName}
            placeholder="可以留空"
            accessibilityLabel="称呼"
          />
        </Field>
        <Field
          label="执行权重"
          hint={weightOk ? '0–100，估时的折扣系数' : '请输入 0–100 的整数'}>
          <MonoInput
            value={weight}
            onChangeText={setWeight}
            keyboardType="number-pad"
            accessibilityLabel="执行权重"
          />
        </Field>

        {message ? (
          <MonoText type="caption" color={message.tone === 'error' ? 'danger' : 'sub'}>
            {message.text}
          </MonoText>
        ) : null}

        <Btn
          label={busy ? '正在保存…' : '保存设置'}
          variant="primary"
          onPress={() => void save()}
          disabled={busy || !weightOk}
          full
        />
      </Card>

      <Card title="外观">
        <LevelPicker
          ask="界面配色"
          options={THEME_OPTIONS}
          value={modeToIndex(mode)}
          onChange={(index) => setMode(indexToMode(index))}
        />
      </Card>

      <Card title="后端">
        <View>
          <Row label="地址" value={API_BASE_URL} />
          <Row
            label="当前计划"
            value={
              plan
                ? `#${plan.id} · v${plan.version} · ${planStatusLabel(plan.status)}`
                : '还没有计划'
            }
          />
          <Row
            label="周期"
            value={plan ? `${formatMonthDay(plan.start_date)} – ${formatMonthDay(plan.end_date)}` : '—'}
          />
        </View>
        <MonoText type="caption" color="faint">
          真机连不上时，先确认这台设备和后端在同一网段；Android 模拟器要用 10.0.2.2。
        </MonoText>
      </Card>

      <Btn label="退出登录" onPress={() => void signOut()} />
    </Screen>
  );
}

/** 一行「字段 → 值」，值右对齐。 */
function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <MonoText type="sub" color="sub">
        {label}
      </MonoText>
      <MonoText type="sub" style={styles.rowValue} numberOfLines={2}>
        {value}
      </MonoText>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: MonoSpace.four,
    minHeight: 36,
    paddingVertical: MonoSpace.two,
  },
  rowValue: { flexShrink: 1, flexGrow: 1, textAlign: 'right' },
});
