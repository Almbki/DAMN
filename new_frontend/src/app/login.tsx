import { useRouter, type Href } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { AuthLayout } from '@/components/auth/auth-layout';
import { Button } from '@/components/ui/button';
import { InlineNotice } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { TextField } from '@/components/ui/text-field';
import { Space } from '@/constants/tokens';
import { authErrorMessage, validateEmail } from '@/domain/auth';
import { useSession } from '@/state/session';
import { useTheme } from '@/state/theme';

export default function LoginScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const session = useSession();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const visibleError = error ?? session.error;

  async function submit() {
    const emailError = validateEmail(email);
    const passwordError = password ? null : '请填写密码。';
    setError(emailError ?? passwordError);
    if (emailError || passwordError || submitting) return;

    setSubmitting(true);
    setError(null);
    try {
      await session.login(email.trim(), password);
    } catch (caught) {
      setError(authErrorMessage(caught, 'login'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="登录"
      subtitle="登录后继续你的计划、执行记录与三层用户模型。">
      {visibleError ? (
        <InlineNotice
          message={visibleError}
          onDismiss={() => {
            setError(null);
            session.clearError();
          }}
        />
      ) : null}
      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <TextField
            label="邮箱"
            value={email}
            onChangeText={(value) => {
              setEmail(value);
              if (error) setError(null);
            }}
            placeholder="you@example.com"
            keyboardType="email-address"
            autoFocus
            background={colors.surfaceContainerLowest}
          />
          <TextField
            label="密码"
            value={password}
            onChangeText={(value) => {
              setPassword(value);
              if (error) setError(null);
            }}
            placeholder="至少 8 位"
            secureTextEntry
            background={colors.surfaceContainerLowest}
          />
          <Button
            label={submitting ? '登录中…' : '登录'}
            variant="filled"
            disabled={submitting}
            onPress={() => void submit()}
          />
          <Button
            label="还没有账号？注册"
            variant="text"
            onPress={() => router.push('/register' as Href)}
          />
        </View>
      </Surface>
    </AuthLayout>
  );
}

const styles = StyleSheet.create({
  card: { padding: Space.xl, gap: Space.lg },
});