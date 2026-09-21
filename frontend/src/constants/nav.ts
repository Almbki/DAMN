import type { IconName } from '@/components/ui/icon';

/**
 * The four destinations. Daily feedback now lives at the bottom of 待办, so it
 * is no longer its own tab.
 */
export const NAV = [
  { href: '/', label: '待办', title: '待办', icon: 'list' as IconName },
  { href: '/profile', label: '画像', title: '画像', icon: 'chart' as IconName },
  { href: '/goal', label: '目标', title: '目标', icon: 'target' as IconName },
  { href: '/settings', label: '设置', title: '设置', icon: 'sliders' as IconName },
] as const;

export type NavItem = (typeof NAV)[number];
