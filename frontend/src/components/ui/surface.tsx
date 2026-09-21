import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { Elevation, Radius, type ElevationLevel, type ThemeColors } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/** Compose an ambient + key shadow with the micro-skeuomorphic edge light. */
export function shadowFor(level: ElevationLevel, highlight = true): string | undefined {
  if (level === 'level0') return highlight ? Elevation.highlight : undefined;
  return highlight ? `${Elevation.highlight}, ${Elevation[level]}` : Elevation[level];
}

type Tone = 'lowest' | 'low' | 'container' | 'high' | 'page';

const TONE_KEY: Record<Tone, keyof ThemeColors> = {
  lowest: 'surfaceContainerLowest',
  low: 'surfaceContainerLow',
  container: 'surfaceContainer',
  high: 'surfaceContainerHigh',
  page: 'surface',
};

export function Surface({
  children,
  level = 'level1',
  radius = 'lg',
  tone = 'lowest',
  highlight = true,
  color,
  bordered = false,
  style,
  contentStyle,
}: {
  children?: React.ReactNode;
  level?: ElevationLevel;
  radius?: keyof typeof Radius;
  tone?: Tone;
  highlight?: boolean;
  color?: string;
  bordered?: boolean;
  style?: StyleProp<ViewStyle>;
  contentStyle?: StyleProp<ViewStyle>;
}) {
  const { colors } = useTheme();
  return (
    <View
      style={[
        styles.base,
        {
          backgroundColor: color ?? colors[TONE_KEY[tone]],
          borderRadius: Radius[radius],
          borderWidth: bordered ? 1 : 0,
          borderColor: colors.outlineVariant,
          boxShadow: shadowFor(level, highlight),
        },
        style,
      ]}>
      {contentStyle ? <View style={contentStyle}>{children}</View> : children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    overflow: 'hidden',
  },
});
