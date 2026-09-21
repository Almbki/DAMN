/**
 * The four destinations. Order is the visual order in the sidebar and the
 * bottom bar. Every one is a first-level page — there are no sub-pages.
 *
 * `icon` keys into `components/icons.tsx`; it is a plain string so this file
 * stays free of any component import.
 */
export const NAV = [
  { href: '/', label: 'TODO', title: 'TODO', icon: 'todo' },
  { href: '/profile', label: '画像', title: '画像', icon: 'profile' },
  { href: '/goals', label: 'GOAL', title: 'GOAL', icon: 'goal' },
  { href: '/settings', label: '设置', title: '设置', icon: 'settings' },
] as const;

export type NavItem = (typeof NAV)[number];
export type NavIconKey = NavItem['icon'];
