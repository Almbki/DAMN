/**
 * 导航壳：宽屏左侧栏 / 窄屏底部栏。
 *
 * 照新模板复刻：
 * - 宽屏（≥ 768）是一列 240px 的侧栏，顶部 logo、底部页脚；
 * - 窄屏是一条贴底的四项导航。
 *
 * 选中态用左侧 3px 墨色竖线 + 灰底（侧栏），底栏用颜色与字重。
 *
 * 用核心 `expo-router` 的 `Link` 做导航（不经过 headless tabs 的显隐状态机 ——
 * 那套机制在切换动画未结束时会让页面输入被吃掉，是上一版踩过的坑）。
 * 图标：项目没有装 svg / 图标库，这里**只用文字标签**，不引入新依赖。
 */

import { Link, usePathname } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { MonoText } from '@/components/mono';
import { MonoBreakpoint, MonoRadius, MonoSpace } from '@/constants/mono';
import { TABS, type TabDef } from '@/constants/tabs';
import { useMono } from '@/hooks/use-mono';

export type NavPlacement = 'bottom' | 'rail';

/** 宽于此值改用竖栏。与 `constants/mono.ts` 的 `MonoBreakpoint` 保持一致。 */
export const RAIL_BREAKPOINT = MonoBreakpoint;
/** 竖栏宽度。 */
export const RAIL_WIDTH = 240;

export function NavRail({ placement }: { placement: NavPlacement }) {
  const insets = useSafeAreaInsets();
  const c = useMono();
  const vertical = placement === 'rail';

  const pathname = usePathname();
  const normalized = pathname.replace(/\/+$/, '') || '/';
  const activeIndex = Math.max(
    0,
    TABS.findIndex((tab) => (String(tab.href).replace(/\/+$/, '') || '/') === normalized),
  );

  if (vertical) {
    return (
      <View
        style={[
          styles.rail,
          {
            backgroundColor: c.panel,
            borderRightColor: c.border,
            paddingTop: insets.top + MonoSpace.five,
            paddingBottom: insets.bottom + MonoSpace.five,
          },
        ]}>
        <View style={styles.logoWrap}>
          <MonoText type="logo">DAMN</MonoText>
        </View>

        <View>
          {TABS.map((tab, index) => (
            <NavItem key={tab.name} tab={tab} active={index === activeIndex} vertical />
          ))}
        </View>

        <View style={[styles.footer, { borderTopColor: c.border }]}>
          <MonoText type="caption" color="faint">
            Agentic Modified
          </MonoText>
          <MonoText type="caption" color="faint">
            No-more-delay
          </MonoText>
        </View>
      </View>
    );
  }

  return (
    <View
      style={[
        styles.bottom,
        {
          backgroundColor: c.bg,
          borderTopColor: c.border,
          paddingBottom: insets.bottom + MonoSpace.two,
        },
      ]}>
      {TABS.map((tab, index) => (
        <NavItem key={tab.name} tab={tab} active={index === activeIndex} vertical={false} />
      ))}
    </View>
  );
}

function NavItem({ tab, active, vertical }: { tab: TabDef; active: boolean; vertical: boolean }) {
  const c = useMono();
  const [hovered, setHovered] = useState(false);

  return (
    <Link href={tab.href} asChild>
      <Pressable
        accessibilityRole="link"
        accessibilityState={{ selected: active }}
        accessibilityLabel={tab.label}
        onHoverIn={() => setHovered(true)}
        onHoverOut={() => setHovered(false)}
        style={({ pressed }) => [
          vertical ? styles.railItem : styles.bottomItem,
          vertical && { borderLeftColor: active ? c.strong : 'transparent' },
          active ? { backgroundColor: c.active } : hovered ? { backgroundColor: c.hover } : null,
          pressed && { opacity: 0.6 },
        ]}>
        <MonoText
          type={vertical ? (active ? 'bodyStrong' : 'body') : 'micro'}
          numberOfLines={1}
          style={{
            color: active ? c.text : c.sub,
            fontWeight: !vertical && active ? '700' : undefined,
          }}>
          {tab.label}
        </MonoText>
      </Pressable>
    </Link>
  );
}

const styles = StyleSheet.create({
  rail: {
    width: RAIL_WIDTH,
    flexShrink: 0,
    borderRightWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 0,
  },
  logoWrap: {
    paddingHorizontal: MonoSpace.five,
    marginBottom: MonoSpace.six,
  },
  railItem: {
    minHeight: 46,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: MonoSpace.five,
    borderLeftWidth: 3,
    borderRadius: 0,
  },
  footer: {
    marginTop: 'auto',
    paddingTop: MonoSpace.five,
    paddingHorizontal: MonoSpace.five,
    borderTopWidth: StyleSheet.hairlineWidth,
    gap: MonoSpace.one,
  },

  bottom: {
    flexDirection: 'row',
    alignItems: 'stretch',
    borderTopWidth: StyleSheet.hairlineWidth,
    paddingTop: MonoSpace.two,
    paddingHorizontal: MonoSpace.two,
  },
  bottomItem: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 0,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: MonoRadius.sm,
    gap: 2,
  },
});

/** 供根布局决定用哪一档；避免在别处重复魔法数字。 */
export function navPlacement(width: number): NavPlacement {
  return width >= RAIL_BREAKPOINT ? 'rail' : 'bottom';
}
