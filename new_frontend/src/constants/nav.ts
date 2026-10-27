import type { IconName } from '@/components/ui/icon';

/** The five destinations. Daily feedback sits next to 待办. */
export const NAV = [
  { href: '/', label: '待办', title: '待办', icon: 'list' as IconName },
  { href: '/feedback', label: '反馈', title: '反馈', icon: 'flag' as IconName },
  { href: '/profile', label: '画像', title: '画像', icon: 'chart' as IconName },
  { href: '/goal', label: '目标', title: '目标', icon: 'target' as IconName },
  { href: '/settings', label: '设置', title: '设置', icon: 'sliders' as IconName },
] as const;

export type NavItem = (typeof NAV)[number];

export type RouteMeta = {
  /** Header title for this route. */
  title: string;
  /** Which nav item should read as selected. `null` means none of them. */
  navHref: string | null;
  /** Show a back button in the header. */
  back?: boolean;
  /** The page draws its own scroll view (used to pin fixed actions). */
  selfScroll?: boolean;
};

/**
 * Explicit route metadata. Without this, any route outside the tabs
 * (e.g. /profile-details) falls back to the first nav item and reads as 待办.
 */
export const ROUTES: Record<string, RouteMeta> = {
  '/': { title: '待办', navHref: '/' },
  '/feedback': { title: '反馈', navHref: '/feedback', selfScroll: true },
  '/profile': { title: '画像', navHref: '/profile' },
  '/goal': { title: '目标', navHref: '/goal', selfScroll: true },
  '/settings': { title: '设置', navHref: '/settings' },
  '/goal-sets': { title: '目标集', navHref: '/goal', back: true, selfScroll: true },
  '/profile-details': { title: '基础档案', navHref: '/profile', back: true },
  '/assessment': { title: '初始画像', navHref: '/profile', back: true },
  '/developer': { title: '模型运行时', navHref: '/settings', back: true },
};

export function routeMetaFor(pathname: string): RouteMeta {
  const key = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
  return ROUTES[key] ?? { title: 'DAMN', navHref: null };
}
