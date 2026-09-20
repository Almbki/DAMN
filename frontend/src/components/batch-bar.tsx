import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

type Props = {
  count: number;
  onComplete: () => void;
  onReopen: () => void;
  onToday: () => void;
  onTomorrow: () => void;
  onDelete: () => void;
  onExit: () => void;
};

export function BatchBar({
  count,
  onComplete,
  onReopen,
  onToday,
  onTomorrow,
  onDelete,
  onExit,
}: Props) {
  const { colors } = useTheme();

  return (
    <View style={[styles.bar, { borderColor: colors.lineStrong, backgroundColor: colors.paper }]}>
      <Text style={[styles.count, { color: colors.ink }]}>
        已选 <Text style={styles.mono}>{count}</Text> 项
      </Text>
      <View style={styles.actions}>
        <Action label="完成" onPress={onComplete} disabled={count === 0} />
        <Action label="标记未完成" onPress={onReopen} disabled={count === 0} />
        <Action label="改到今天" onPress={onToday} disabled={count === 0} />
        <Action label="改到明天" onPress={onTomorrow} disabled={count === 0} />
        <Action label="删除" onPress={onDelete} disabled={count === 0} />
        <Action label="退出多选" onPress={onExit} />
      </View>
    </View>
  );
}

function Action({
  label,
  onPress,
  disabled = false,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  const { colors } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled}
      onPress={onPress}
      style={[styles.action, { borderColor: colors.line, opacity: disabled ? 0.38 : 1 }]}>
      <Text style={[styles.actionText, { color: colors.ink }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  bar: {
    borderWidth: 1,
    borderRadius: Radius.md,
    padding: Space.md,
    gap: Space.md,
  },
  count: {
    fontSize: Type.body,
  },
  mono: {
    fontFamily: 'IBMPlexMono_500Medium',
  },
  actions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  action: {
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.md,
    minHeight: 36,
    justifyContent: 'center',
  },
  actionText: {
    fontSize: Type.small,
  },
});
