import { Link, usePathname, useRouter } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { IconButton } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { useInteraction } from '@/components/ui/interaction';
import { NAV, routeMetaFor, type NavItem } from '@/constants/nav';
import { Elevation, Layout, Line, Radius, Space, Type } from '@/constants/tokens';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

function useWide() {
  const { width } = useWindowDimensions();
  // Static rendering has no real window yet; the first frame must be narrow.
  return width > 0 && width >= Layout.breakpoint;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { colors } = useTheme();
  const { actionError, clearActionError } = usePlan();
  const insets = useSafeAreaInsets();
  const wide = useWide();
  const pathname = usePathname();
  const router = useRouter();
  const meta = routeMetaFor(pathname);

  function goBack() {
    if (router.canGoBack()) router.back();
    else router.replace('/profile');
  }

  const content = (
    <View
      style={[
        styles.content,
        {
          maxWidth: Layout.contentMax,
          paddingHorizontal: wide ? Layout.padWide : Layout.padNarrow,
          paddingTop: wide ? Space.xxl : Space.xl,
          paddingBottom: (wide ? Space.xxl : Space.xl) + (wide ? insets.bottom : 0),
        },
      ]}>
      {children}
    </View>
  );

  return (
    <View
      style={[
        styles.root,
        {
          backgroundColor: colors.surface,
          flexDirection: wide ? 'row' : 'column',
          paddingLeft: insets.left,
          paddingRight: insets.right,
        },
      ]}>
      {wide ? (
        <NavigationRail
          activeHref={meta.navHref}
          topInset={insets.top}
          bottomInset={insets.bottom}
        />
      ) : null}

      <View style={styles.main}>
        <View
          style={[
            styles.header,
            {
              height: Layout.headerHeight + insets.top,
              paddingTop: insets.top,
              paddingHorizontal: wide ? Layout.padWide : Layout.padNarrow,
              borderBottomColor: colors.outlineVariant,
              backgroundColor: colors.surface,
            },
          ]}>
          <View style={styles.headerLeft}>
            {meta.back ? (
              <IconButton name="arrowLeft" label="返回" size={44} onPress={goBack} />
            ) : null}
            <Text
              accessibilityRole="header"
              numberOfLines={1}
              style={[styles.headerTitle, { color: colors.ink }]}>
              {meta.title}
            </Text>
          </View>
        </View>

        {actionError ? (
          <View
            accessibilityRole="alert"
            accessibilityLiveRegion="polite"
            style={[
              styles.errorBanner,
              {
                backgroundColor: colors.errorContainer,
                borderBottomColor: colors.error,
                paddingHorizontal: wide ? Layout.padWide : Layout.padNarrow,
              },
            ]}>
            <Icon name="flag" size={16} color={colors.onErrorContainer} />
            <Text style={[styles.errorText, { color: colors.onErrorContainer }]} numberOfLines={3}>
              {actionError}
            </Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="关闭错误提示"
              onPress={clearActionError}
              hitSlop={8}
              style={styles.errorDismiss}>
              <Icon name="close" size={16} color={colors.onErrorContainer} />
            </Pressable>
          </View>
        ) : null}

        {meta.selfScroll ? (
          <View style={styles.contentHost}>{content}</View>
        ) : (
          <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
            {content}
          </ScrollView>
        )}
      </View>

      {wide ? null : (
        <BottomNav activeHref={meta.navHref} bottomInset={insets.bottom} />
      )}
    </View>
  );
}

function NavigationRail({
  activeHref,
  topInset,
  bottomInset,
}: {
  activeHref: string | null;
  topInset: number;
  bottomInset: number;
}) {
  const { colors } = useTheme();
  return (
    <View
      style={[
        styles.rail,
        {
          width: Layout.railWidth,
          paddingTop: topInset + Space.lg,
          paddingBottom: Space.md + bottomInset,
          backgroundColor: colors.surfaceContainer,
          borderRightColor: colors.outlineVariant,
        },
      ]}>
      <Text style={[styles.wordmark, { color: colors.primary }]}>DAMN</Text>

      <View style={styles.navList}>
        {NAV.map((item) => (
          <NavLink key={item.href} item={item} active={item.href === activeHref} variant="rail" />
        ))}
      </View>

      <View style={[styles.railFooter, { borderTopColor: colors.outlineVariant }]}>
        <Text style={[styles.footerLine, { color: colors.inkFaint }]}>Agentic</Text>
        <Text style={[styles.footerLine, { color: colors.inkFaint }]}>Modified</Text>
      </View>
    </View>
  );
}

function BottomNav({
  activeHref,
  bottomInset,
}: {
  activeHref: string | null;
  bottomInset: number;
}) {
  const { colors } = useTheme();
  return (
    <View
      style={[
        styles.bottomNav,
        {
          backgroundColor: colors.surfaceContainer,
          borderTopColor: colors.outlineVariant,
          height: Layout.navBarHeight + bottomInset,
          paddingBottom: Space.sm + bottomInset,
        },
      ]}>
      {NAV.map((item) => (
        <NavLink key={item.href} item={item} active={item.href === activeHref} variant="bar" />
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
          numberOfLines={1}
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
  headerLeft: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
    minWidth: 0,
  },
  headerTitle: {
    flexShrink: 1,
    fontSize: Type.titleLarge,
    fontWeight: '600',
  },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
    borderBottomWidth: 1,
    paddingVertical: Space.sm,
  },
  errorText: {
    flex: 1,
    fontSize: Type.labelLarge,
    lineHeight: Type.labelLarge * Line.normal,
  },
  errorDismiss: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: Radius.pill,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
  },
  contentHost: {
    flex: 1,
    minHeight: 0,
  },
  content: {
    width: '100%',
    alignSelf: 'center',
    // Lets a page fill the viewport so its absolute bottom-right FABs pin to the
    // bottom instead of floating right after short content.
    flexGrow: 1,
  },
  rail: {
    borderRightWidth: 1,
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
    // Five tabs have to share narrow phones; keep the pill inside its slot.
    width: 56,
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
  },
  barItem: {
    flex: 1,
    minWidth: 0,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Space.xs,
  },
  barLabel: {
    maxWidth: '100%',
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.tight,
  },
});
