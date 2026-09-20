/**
 * 取当前明暗下的黑白配色。
 *
 * 复用现有的 `useScheme()` —— 它已经处理了「手动切换 > 系统」的优先级，
 * 所以这里跟着 `?theme=` / 设置页里的切换一起变，不需要另起一套状态。
 */

import { MonoPalette, type MonoColors } from '@/constants/mono';
import { useScheme } from '@/hooks/use-theme';

export function useMono(): MonoColors {
  return MonoPalette[useScheme()];
}
