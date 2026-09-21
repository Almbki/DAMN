import { Link, usePathname } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  Animated,
  Easing as RNEasing,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';

import { NAV_ICONS } from '@/components/icons';
import { HeaderControlsContext, type HeaderControls } from '@/components/shell/header-controls';
import { Surface } from '@/components/surface';
import { useInteraction } from '@/components/ui/interaction';
import { useRipple } from '@/components/ui/ripple';
import { NAV, type NavItem } from '@/constants/nav';
import {
  Duration,
  Layout,
  Line,
  Motion,
  Radius,
  RingWidth,
  Space,
  Type,
} from '@/constants/tokens';
import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { useTheme } from '@/state/theme';

/** The bottom bar's active pill, in points. */
const TAB_PILL_WIDTH = 56;
const TAB_PILL_HEIGHT = 30;

function useWide() {
  const { width } = useWindowDimensions();
  // Static rendering has no real window yet; the first frame must be narrow.
  return width > 0 && width >= Layout.breakpoint;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { colors } = useTheme();
  const wide = useWide();
  const pathname = usePathname();
  const [headerControls, setHeaderControls] = useState<HeaderControls>({});

  return (
    <HeaderControlsContext.Provider value={setHeaderControls}>
      <View
        style={[
          styles.root,
          { backgroundColor: colors.paper, flexDirection: wide ? 'row' : 'column' },
        ]}>
        {wide ? <Sidebar pathname={pathname} /> : null}

        <View style={styles.main}>
          <View
            style={[
              styles.header,
              {
                height: Layout.headerHeight,
                paddingHorizontal: wide ? Layout.padWide : Layout.padNarrow,
                borderBottomColor: colors.line,
                backgroundColor: colors.paper,
              },
            ]}>
            <View style={styles.headerSide}>{headerControls.left}</View>
            <View style={styles.headerSide}>{headerControls.right}</View>
          </View>

          <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
            <View
              style={[
                styles.content,
                {
                  maxWidth: Layout.contentMax,
                  paddingHorizontal: wide ? Layout.padWide : Layout.padNarrow,
                  paddingVertical: wide ? Space.xxl : Space.xl,
                },
              ]}>
              {children}
            </View>
          </ScrollView>
        </View>

        {wide ? null : <BottomNav pathname={pathname} />}
      </View>
    </HeaderControlsContext.Provider>
  );
}

function Sidebar({ pathname }: { pathname: string }) {
  const { colors } = useTheme();
  return (
    <View
      style={[
        styles.sidebar,
        {
          width: Layout.sidebarWidth,
          backgroundColor: colors.panel,
          borderRightColor: colors.line,
        },
      ]}>
      <Text style={[styles.wordmark, { color: colors.ink }]}>DAMN</Text>

      <View style={styles.navList}>
        {NAV.map((item) => (
          <NavLink key={item.href} item={item} active={item.href === pathname} variant="rail" />
        ))}
      </View>

      <View style={[styles.sidebarFooter, { borderTopColor: colors.line }]}>
        <Text style={[styles.footerLine, { color: colors.inkFaint }]}>Agentic Modified</Text>
        <Text style={[styles.footerLine, { color: colors.inkFaint }]}>No-more-delay</Text>
      </View>
    </View>
  );
}

/**
 * Bottom bar with an MD pill that slides between the active tabs.
 *
 * The pill is a `translateX` on a single absolutely positioned node: position is
 * `activeIndex × itemWidth`, and `itemWidth` comes from measuring the container,
 * so there is no wrapping and no per-item layout math.
 */
function BottomNav({ pathname }: { pathname: string }) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const [width, setWidth] = useState(0);
  const [slide] = useState(() => new Animated.Value(0));
  const activeIndex = Math.max(
    0,
    NAV.findIndex((item) => item.href === pathname),
  );
  const itemWidth = width > 0 ? width / NAV.length : 0;

  useEffect(() => {
    const to = activeIndex * itemWidth;
    if (reduced || itemWidth === 0) {
      slide.setValue(to);
      return;
    }
    const animation = Animated.timing(slide, {
      toValue: to,
      duration: Duration.medium,
      easing: RNEasing.bezier(0.05, 0.7, 0.1, 1),
      useNativeDriver: Motion.nativeDriver,
    });
    animation.start();
    return () => animation.stop();
  }, [activeIndex, itemWidth, reduced, slide]);

  return (
    <View
      onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
      style={[
        styles.bottomNav,
        { backgroundColor: colors.panel, borderTopColor: colors.line, height: Layout.navHeight },
      ]}>
      {itemWidth > 0 ? (
        <Animated.View
          pointerEvents="none"
          style={[
            styles.sliderTrack,
            {
              width: TAB_PILL_WIDTH,
              height: TAB_PILL_HEIGHT,
              left: (itemWidth - TAB_PILL_WIDTH) / 2,
              transform: [{ translateX: slide }],
            },
          ]}>
          <Surface
            elevation="raised"
            radius={Radius.full}
            background={colors.navPill}
            style={styles.slider}
          />
        </Animated.View>
      ) : null}

      {NAV.map((item) => (
        <NavLink key={item.href} item={item} active={item.href === pathname} variant="tab" />
      ))}
    </View>
  );
}

function NavLink({
  item,
  active,
  variant,
}: {
  item: NavItem;
  active: boolean;
  variant: 'rail' | 'tab';
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const ripple = useRipple(colors.ripple);
  const isRail = variant === 'rail';
  const Icon = NAV_ICONS[item.icon];
  const tint = active ? colors.accent : colors.inkMuted;

  return (
    <Link href={item.href} asChild>
      <Pressable
        accessibilityRole="link"
        accessibilityState={{ selected: active }}
        {...handlers}
        onLayout={ripple.onLayout}
        onPressIn={ripple.onPressIn}
        style={StyleSheet.flatten([
          isRail ? styles.railItem : styles.tabItem,
          {
            borderLeftColor: isRail ? (active ? colors.accent : 'transparent') : undefined,
            backgroundColor: hovered ? colors.hover : 'transparent',
          },
        ])}>
        {ripple.node}
        <View
          style={
            isRail ? styles.railContent : [styles.tabContent, active ? styles.tabContentActive : null]
          }>
          <Icon size={22} color={tint} />
          <Text
            style={[
              isRail ? styles.railLabel : styles.tabLabel,
              {
                color: active ? colors.ink : colors.inkMuted,
                fontWeight: active ? '700' : '400',
              },
            ]}>
            {item.label}
          </Text>
        </View>
        {focused ? (
          <View pointerEvents="none" style={[styles.ring, { borderColor: colors.accent }]} />
        ) : null}
      </Pressable>
    </Link>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  main: {
    flex: 1,
    minWidth: 0,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
  },
  headerSide: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
    minWidth: 0,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
  },
  content: {
    width: '100%',
    alignSelf: 'center',
  },
  sidebar: {
    borderRightWidth: 1,
    paddingTop: Space.xl,
    paddingBottom: Space.lg,
  },
  wordmark: {
    fontSize: Type.title,
    fontWeight: '700',
    letterSpacing: 2,
    paddingHorizontal: Space.xl,
    paddingBottom: Space.xxl,
  },
  navList: {
    flex: 1,
  },
  railItem: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Space.md,
    paddingHorizontal: Space.xl,
    paddingLeft: Space.xl - 3,
    borderLeftWidth: 3,
    overflow: 'hidden',
  },
  railContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
  },
  railLabel: {
    fontSize: Type.body,
  },
  sidebarFooter: {
    borderTopWidth: 1,
    paddingHorizontal: Space.xl,
    paddingTop: Space.lg,
    gap: 2,
  },
  footerLine: {
    fontSize: Type.micro,
  },
  bottomNav: {
    flexDirection: 'row',
    borderTopWidth: 1,
  },
  sliderTrack: {
    position: 'absolute',
    top: 4,
  },
  slider: {
    flex: 1,
  },
  tabItem: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'flex-start',
    paddingTop: Space.sm,
    overflow: 'hidden',
  },
  tabContent: {
    alignItems: 'center',
    gap: Space.xs,
  },
  tabContentActive: {
    transform: [{ translateY: -2 }],
  },
  tabLabel: {
    fontSize: Type.small,
    lineHeight: Type.small * Line.tight,
  },
  ring: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderWidth: RingWidth,
  },
});
