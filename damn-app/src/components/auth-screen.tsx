/**
 * 登录 / 注册。**没有后端就没有这个产品** —— 所以它是第一屏，不是弹窗。
 *
 * 样式跟着新的黑白模板走：居中的一列表单、1px 边框、无阴影、无强调色。
 * 页脚保留后端地址与一次 `/health` 探活结果 —— 真机连不上时，
 * 看一眼就知道该去改 IP 还是去开后端。
 */

import { useCallback, useEffect, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';

import { describeApiError } from '@/api/client';
import { API_BASE_URL } from '@/api/config';
import * as endpoints from '@/api/endpoints';
import { Btn, Field, MonoInput, MonoRule, MonoText } from '@/components/mono';
import { MonoSpace } from '@/constants/mono';
import { useMono } from '@/hooks/use-mono';
import { useSession } from '@/session/session-provider';

type Mode = 'signIn' | 'signUp';

/** `/health` 的探活结果，只用来在页脚给个提示。 */
type Probe = { state: 'checking' | 'ok' | 'failed'; detail: string };

export function AuthScreen() {
  const c = useMono();
  const { signIn, signUp } = useSession();

  const [mode, setMode] = useState<Mode>('signIn');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [probe, setProbe] = useState<Probe>({ state: 'checking', detail: '正在探活…' });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const info = await endpoints.health();
        if (cancelled) return;
        setProbe({ state: 'ok', detail: `${info.app} ${info.version} · ${info.environment}` });
      } catch (cause) {
        if (cancelled) return;
        setProbe({ state: 'failed', detail: describeApiError(cause) });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const submit = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      if (mode === 'signUp') {
        await signUp(email, password, displayName);
      } else {
        await signIn(email, password);
      }
    } catch (cause) {
      setError(describeApiError(cause));
    } finally {
      setBusy(false);
    }
  }, [mode, email, password, displayName, signIn, signUp]);

  const emailOk = /.+@.+\..+/.test(email.trim());
  // 后端要求 8–128 位（Pydantic 会拦），前端先挡一道，少一次白跑的请求
  const passwordOk = password.length >= 8 && password.length <= 128;
  const canSubmit = emailOk && passwordOk && !busy;

  return (
    <View style={[styles.root, { backgroundColor: c.bg }]}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.card}>
          <MonoText type="logo">DAMN</MonoText>
          <View style={styles.heading}>
            <MonoText type="display">{mode === 'signIn' ? '登录' : '注册'}</MonoText>
            <MonoText type="sub" color="sub">
              {mode === 'signIn'
                ? '计划是私人的，得挂在账号下面。'
                : '只要邮箱和一个 8 位以上的密码。'}
            </MonoText>
          </View>

          {mode === 'signUp' ? (
            <Field label="称呼">
              <MonoInput
                value={displayName}
                onChangeText={setDisplayName}
                autoCapitalize="none"
                placeholder="可以留空"
                accessibilityLabel="显示名称"
              />
            </Field>
          ) : null}

          <Field label="邮箱">
            <MonoInput
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              placeholder="you@example.com"
              accessibilityLabel="邮箱"
            />
          </Field>

          <Field label="密码" hint={password && !passwordOk ? '至少 8 位' : undefined}>
            <MonoInput
              value={password}
              onChangeText={setPassword}
              autoCapitalize="none"
              autoCorrect={false}
              secureTextEntry
              placeholder="至少 8 位"
              accessibilityLabel="密码"
              onSubmitEditing={() => {
                if (canSubmit) void submit();
              }}
            />
          </Field>

          {error ? (
            <MonoText type="caption" color="danger">
              {error}
            </MonoText>
          ) : null}

          <Btn
            label={busy ? '正在连接…' : mode === 'signIn' ? '进去' : '注册并进去'}
            variant="primary"
            onPress={() => void submit()}
            disabled={!canSubmit}
            full
          />
          <Btn
            label={mode === 'signIn' ? '还没有账号，去注册' : '已经有账号了，去登录'}
            onPress={() => {
              setMode((current) => (current === 'signIn' ? 'signUp' : 'signIn'));
              setError(null);
            }}
            full
          />

          <MonoRule />

          <View style={styles.footer}>
            <MonoText type="micro" color="faint">
              后端 {API_BASE_URL}
            </MonoText>
            <MonoText type="micro" color={probe.state === 'failed' ? 'danger' : 'faint'}>
              {probe.state === 'checking'
                ? '正在探活…'
                : probe.state === 'ok'
                  ? `已连上 · ${probe.detail}`
                  : `连不上 · ${probe.detail}`}
            </MonoText>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  scroll: {
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: MonoSpace.five,
  },
  card: {
    width: '100%',
    maxWidth: 400,
    gap: MonoSpace.four,
  },
  heading: { gap: MonoSpace.two },
  footer: { gap: MonoSpace.one },
});
