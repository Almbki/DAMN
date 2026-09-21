import { StyleSheet, View, type StyleProp, type ViewProps, type ViewStyle } from 'react-native';

import { ElevationTokens, Radius, RingWidth, type Elevation } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

type SurfaceProps = ViewProps & {
  /** One of the four heights. Everything visual about height lives here. */
  elevation?: Elevation;
  radius?: number;
  /** A 1px divider in `line`; the static-content counterpart to a shadow. */
  hairline?: boolean;
  /** Draw a 1.5px accent stroke over the surface (keyboard focus only). */
  ring?: boolean;
  /** Override the surface fill (e.g. the primary button's accent). */
  background?: string;
  style?: StyleProp<ViewStyle>;
};

/**
 * The single place shadows and elevation layers are implemented.
 *
 * Light `raised`/`overlay` cast a cool grey-green shadow; dark mode never casts
 * an outer shadow, it lifts the surface with a white overlay plus a top hairline
 * highlight. `inset` is the "already happened" state. A focus ring is always
 * painted on top of the shadow.
 *
 * Height discipline (see §2 of the design draft): `raised` means "sits above the
 * page" — cards, buttons, floating layers. List rows, blocks and charts stay
 * `flat` + hairline; never shadow a static row.
 */
export function Surface({
  elevation = 'flat',
  radius = Radius.md,
  hairline = false,
  ring = false,
  background,
  style,
  children,
  ...rest
}: SurfaceProps) {
  const { colors, resolved } = useTheme();
  const tokens = ElevationTokens[resolved][elevation];

  const fill = background ?? defaultFill(elevation, colors);

  return (
    <View
      {...rest}
      style={[
        styles.base,
        { borderRadius: radius },
        fill ? { backgroundColor: fill } : null,
        tokens.boxShadow !== 'none' ? { boxShadow: tokens.boxShadow } : null,
        hairline ? { borderWidth: 1, borderColor: colors.line } : null,
        style,
      ]}>
      {tokens.overlayColor ? (
        <View
          pointerEvents="none"
          style={[StyleSheet.absoluteFill, { backgroundColor: tokens.overlayColor }]}
        />
      ) : null}
      {tokens.highlightColor ? (
        <View
          pointerEvents="none"
          style={[styles.highlight, { backgroundColor: tokens.highlightColor }]}
        />
      ) : null}

      {children}

      {ring ? (
        <View
          pointerEvents="none"
          style={[
            StyleSheet.absoluteFill,
            { borderWidth: RingWidth, borderColor: colors.accent, borderRadius: radius },
          ]}
        />
      ) : null}
    </View>
  );
}

function defaultFill(elevation: Elevation, colors: ReturnType<typeof useTheme>['colors']) {
  if (elevation === 'raised' || elevation === 'overlay') return colors.raised;
  if (elevation === 'inset') return colors.panel;
  return undefined;
}

const styles = StyleSheet.create({
  base: {
    overflow: 'hidden',
  },
  highlight: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 1,
  },
});
