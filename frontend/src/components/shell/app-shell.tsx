import { Link, usePathname } from 'expo-router';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';

import { useInteraction } from '@/components/ui/interaction';
import { NAV, type NavItem } from '@/constants/nav';
import { Layout, Line, Space, Type } from '@/constants/tokens';
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
          <Text style={[styles.headerTitle, { color: colors.ink }]}>{active.title}</Text>
          <ThemeToggle />
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

function BottomNav({ pathname }: { pathname: string }) {
  const { colors } = useTheme();
  return (
    <View
      style={[
        styles.bottomNav,
        { backgroundColor: colors.panel, borderTopColor: colors.line, height: Layout.navHeight },
      ]}>
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
  const isRail = variant === 'rail';

  return (
    <Link href={item.href} asChild>
      <Pressable
        accessibilityRole="link"
        accessibilityState={{ selected: active }}
        {...handlers}
        style={StyleSheet.flatten([
          isRail ? styles.railItem : styles.tabItem,
          {
            borderLeftColor: isRail ? (active ? colors.ink : 'transparent') : undefined,
            borderTopColor: !isRail ? (active ? colors.ink : 'transparent') : undefined,
            backgroundColor: hovered ? colors.hover : 'transparent',
            boxShadow: focused ? `0 0 0 2px ${colors.lineStrong}` : undefined,
          },
        ])}>
        <Text
          style={[
            isRail ? styles.railLabel : styles.tabLabel,
            {
              color: active ? colors.ink : colors.inkMuted,
              fontWeight: active ? '700' : '500',
            },
          ]}>
          {item.label}
        </Text>
      </Pressable>
    </Link>
  );
}

function ThemeToggle() {
  const { colors, mode, cycleMode } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const label = mode === 'light' ? '浅色' : mode === 'dark' ? '深色' : '跟系统';

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`主题：${label}，点击切换`}
      onPress={cycleMode}
      {...handlers}
      style={[
        styles.themeToggle,
        {
          borderColor: colors.line,
          backgroundColor: hovered ? colors.hover : 'transparent',
          boxShadow: focused ? `0 0 0 2px ${colors.lineStrong}` : undefined,
        },
      ]}>
      <Text style={[styles.themeLabel, { color: colors.inkMuted }]}>{label}</Text>
    </Pressable>
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
    fontSize: Type.title,
    fontWeight: '700',
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
    paddingVertical: Space.md,
    paddingHorizontal: Space.xl,
    paddingLeft: Space.xl - 3,
    borderLeftWidth: 3,
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
  tabItem: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    borderTopWidth: 2,
  },
  tabLabel: {
    fontSize: Type.small,
    lineHeight: Type.small * Line.tight,
  },
  themeToggle: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: Space.md,
    paddingVertical: Space.xs,
    minHeight: 30,
    justifyContent: 'center',
  },
  themeLabel: {
    fontSize: Type.small,
  },
});
