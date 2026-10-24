import { StyleSheet, Text, View } from 'react-native';

import { Segmented } from '@/components/ui/segmented';
import { Line, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

const OPTIONS = ['非常不同意', '不同意', '一般', '同意', '非常同意'];

/** Raw 1..5 Likert input. No reverse-scoring happens on the client. */
export function LikertScale({
  value,
  onChange,
  disabled = false,
}: {
  value: number | null;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  const { colors } = useTheme();
  return (
    <View style={styles.wrap}>
      <Segmented
        label="这道描述有多符合你？"
        options={OPTIONS}
        value={value == null ? -1 : value - 1}
        onChange={(index) => onChange(index + 1)}
        disabled={disabled ? [0, 1, 2, 3, 4] : []}
        scroll
        size="sm"
      />
      <Text style={[styles.note, { color: colors.inkMuted }]}>
        1 = 非常不同意 · 5 = 非常同意。按第一反应作答即可。
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: Space.md },
  note: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
});