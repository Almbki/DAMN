/**
 * 导航项的唯一定义处。
 *
 * 严格对应新模板的 4 项：Todo / 用户画像 / 反馈 / 设置。
 * 侧栏与底栏都只 map 这个数组，增删页面改这里一处。
 *
 * 「目标生成」不是单独一页 —— 它并入 Todo 页顶部的输入栏
 * （后端没有「加单条任务」的接口，用户能加的其实是**目标**，由后端拆成任务）。
 */

import type { Href } from 'expo-router';

export type TabKey = 'index' | 'profile' | 'feedback' | 'settings';

export type TabDef = {
  /** 对应 `src/app/<name>.tsx` 的文件名（`index` 是 `/`） */
  name: TabKey;
  href: Href;
  /** 导航栏里的短标签 */
  label: string;
  /** 顶部标题栏文案 */
  title: string;
};

export const TABS: readonly TabDef[] = [
  { name: 'index', href: '/', label: 'Todo', title: 'Todo 列表' },
  { name: 'profile', href: '/profile', label: '用户画像', title: '用户画像' },
  { name: 'feedback', href: '/feedback', label: '反馈', title: '每日反馈' },
  { name: 'settings', href: '/settings', label: '设置', title: '设置' },
] as const;
