import { useRouter, type Href } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { AuthLayout } from '@/components/auth/auth-layout';
import { Button } from '@/components/ui/button';
import { InlineNotice } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { TextField } from '@/components/ui/text-field';
import { Space } from '@/constants/tokens';
import { authErrorMessage, validateEmail, validatePassword } from '@/domain/auth';
import { useSession } from '@/state/session';
import { useTheme } from '@/state/theme';

export default function RegisterScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const session = useSession();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const visibleError = error ?? session.error;

  async function submit() {
    const emailError = validateEmail(email);
    const passwordError = validatePassword(password);
    setError(emailError ?? passwordError);
    if (emailError || passwordError || submitting) return;

    setSubmitting(true);
    setError(null);
    try {
      await session.register({
        email: email.trim(),
        password,
        display_name: displayName.trim() || null,
      });
      // Session becomes authenticated; the route guard moves to onboarding.
    } catch (caught) {
      setError(authErrorMessage(caught, 'register'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="注册"
      subtitle="创建账号后，会先完成一次简短的初始画像，再进入完整平台。">
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
          <TextField
            label="昵称（可选）"
            value={displayName}
            onChangeText={setDisplayName}
            placeholder="怎么称呼你"
            background={colors.surfaceContainerLowest}
          />
          <Button
            label={submitting ? '注册中…' : '注册'}
            variant="filled"
            disabled={submitting}
            onPress={() => void submit()}
          />
          <Button
            label="已有账号？去登录"
            variant="text"
            onPress={() => router.push('/login' as Href)}
          />
        </View>
      </Surface>
    </AuthLayout>
  );
}

const styles = StyleSheet.create({
  card: { padding: Space.xl, gap: Space.lg },
});