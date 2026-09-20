import { StyleSheet, Text, View } from 'react-native';

import { Line, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/**
 * "Why this, now" — the AI decision must be legible and reversible (the Rise
 * post-mortem: being right is not the same as being perceived as right).
 * The mint rule ties it to the live recommendation.
 */
export function WhyNote({ text }: { text: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.row}>
      <View style={[styles.rule, { backgroundColor: colors.mint }]} />
      <Text style={[styles.text, { color: colors.inkMuted }]}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: 12,
  },
  rule: {
    width: 2,
    borderRadius: 1,
  },
  text: {
    flex: 1,
    fontSize: Type.small,
    lineHeight: Type.small * Line.relaxed,
    maxWidth: 560,
  },
});
