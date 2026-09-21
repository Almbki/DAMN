import { Link, usePathname } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { Icon } from '@/components/ui/icon';
import { useInteraction } from '@/components/ui/interaction';
import { NAV, type NavItem } from '@/constants/nav';
import { Elevation, Layout, Line, Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

function useWide() {
  const { width } = useWindowDimensions();
  // Static rendering has no real window yet; the first frame must be narrow.
  return width > 0 && width >= Layout.breakpoint;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { colors } = useTheme();
  const wide = useWide();
  const pathname = usePathname();
  const active = NAV.find((item) => item.href === pathname) ?? NAV[0];

  return (
    <View
      style={[
        styles.root,
        { backgroundColor: colors.surface, flexDirection: wide ? 'row' : 'column' },
      ]}>
      {wide ? <NavigationRail pathname={pathname} /> : null}

      <View style={styles.main}>
        <View
          style={[
            styles.header,
            {
              height: Layout.headerHeight,
              paddingHorizontal: wide ? Layout.padWide : Layout.padNarrow,
              borderBottomColor: colors.outlineVariant,
              backgroundColor: colors.surface,
            },
          ]}>
          <Text style={[styles.headerTitle, { color: colors.ink }]}>{active.title}</Text>
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
  );
}

function NavigationRail({ pathname }: { pathname: string }) {
  const { colors } = useTheme();
  return (
    <View
      style={[
        styles.rail,
        {
          width: Layout.railWidth,
          backgroundColor: colors.surfaceContainer,
          borderRightColor: colors.outlineVariant,
        },
      ]}>
      <Text style={[styles.wordmark, { color: colors.primary }]}>DAMN</Text>

      <View style={styles.navList}>
        {NAV.map((item) => (
          <NavLink key={item.href} item={item} active={item.href === pathname} variant="rail" />
        ))}
      </View>

      <View style={[styles.railFooter, { borderTopColor: colors.outlineVariant }]}>
        <Text style={[styles.footerLine, { color: colors.inkFaint }]}>Agentic</Text>
        <Text style={[styles.footerLine, { color: colors.inkFaint }]}>Modified</Text>
      </View>
    </View>
  );
}

function BottomNav({ pathname }: { pathname: string }) {
  const { colors } = useTheme();
  return (
    <View
      style={[
        styles.bottomNav,
        {
          backgroundColor: colors.surfaceContainer,
          borderTopColor: colors.outlineVariant,
          height: Layout.navBarHeight,
        },
      ]}>
      {NAV.map((item) => (
        <NavLink key={item.href} item={item} active={item.href === pathname} variant="bar" />
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
  variant: 'rail' | 'bar';
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const isRail = variant === 'rail';

  return (
    <Link href={item.href} asChild>
      <Pressable
        accessibilityRole="link"
        accessibilityState={{ selected: active }}
        accessibilityLabel={item.title}
        {...handlers}
        style={StyleSheet.flatten([
          isRail ? styles.railItem : styles.barItem,
          {
            backgroundColor: hovered && !active ? colors.hover : 'transparent',
            boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
          },
        ])}>
        <View
          style={[
            styles.indicator,
            isRail ? styles.indicatorRail : styles.indicatorBar,
            {
              backgroundColor: active ? colors.secondaryContainer : 'transparent',
              boxShadow: active ? Elevation.highlight : undefined,
            },
          ]}>
          <Icon
            name={item.icon}
            size={20}
            color={active ? colors.onSecondaryContainer : colors.inkMuted}
          />
        </View>
        <Text
          style={[
            isRail ? styles.railLabel : styles.barLabel,
            {
              color: active ? colors.ink : colors.inkMuted,
              fontWeight: active ? '600' : '400',
            },
          ]}>
          {item.label}
        </Text>
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
  headerTitle: {
    fontSize: Type.titleLarge,
    fontWeight: '600',
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
  rail: {
    borderRightWidth: 1,
    paddingTop: Space.lg,
    paddingBottom: Space.md,
    alignItems: 'center',
  },
  wordmark: {
    fontSize: Type.titleMedium,
    fontWeight: '700',
    letterSpacing: 2,
    paddingBottom: Space.xl,
  },
  navList: {
    flex: 1,
    alignSelf: 'stretch',
    gap: Space.sm,
  },
  railItem: {
    alignItems: 'center',
    gap: Space.xs,
    paddingVertical: Space.sm,
  },
  indicator: {
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: Radius.lg,
  },
  indicatorRail: {
    width: 56,
    height: 32,
  },
  indicatorBar: {
    width: 64,
    height: 32,
  },
  railLabel: {
    fontSize: Type.labelMedium,
  },
  railFooter: {
    borderTopWidth: 1,
    paddingTop: Space.md,
    alignItems: 'center',
    gap: 2,
  },
  footerLine: {
    fontSize: Type.labelSmall,
  },
  bottomNav: {
    flexDirection: 'row',
    borderTopWidth: 1,
    paddingTop: Space.sm,
    paddingBottom: Space.sm,
  },
  barItem: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Space.xs,
  },
  barLabel: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.tight,
  },
});
