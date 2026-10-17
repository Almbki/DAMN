import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

export default function NotFoundScreen() {
  const { colors } = useTheme();
  const router = useRouter();

  return (
    <View style={styles.page}>
      <Text style={[styles.code, { color: colors.outline }]}>404</Text>
      <Text style={[styles.title, { color: colors.ink }]}>找不到这个页面</Text>
      <Text style={[styles.body, { color: colors.inkMuted }]}>
        链接可能已经过期，或者地址写错了。回到待办继续今天的事。
      </Text>
      <Button
        label="回到待办"
        variant="filled"
        icon="arrowLeft"
        onPress={() => router.replace('/')}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    minHeight: 420,
    alignItems: 'flex-start',
    justifyContent: 'center',
    gap: Space.md,
    paddingVertical: Space.xxxl,
  },
  code: {
    fontFamily: Fonts.mono,
    fontSize: Type.displaySm,
    lineHeight: Type.displaySm * 1.05,
  },
  title: {
    fontSize: Type.headlineSmall,
    fontWeight: '600',
  },
  body: {
    maxWidth: 480,
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
  },
});
