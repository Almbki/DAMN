/**
 * The four destinations, taken verbatim from the reference layout.
 * Order is the visual order in the sidebar and the bottom bar.
 */
export const NAV = [
  { href: '/', label: 'Todo', title: 'Todo' },
  { href: '/profile', label: '用户画像', title: '用户画像' },
  { href: '/feedback', label: '反馈', title: '反馈' },
  { href: '/settings', label: '设置', title: '设置' },
] as const;

export type NavItem = (typeof NAV)[number];
