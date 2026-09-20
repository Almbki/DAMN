import type { ErrorInfo, ReactNode } from 'react';
import { Component } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { MonoPalette, MonoRadius, MonoSpace } from '@/constants/mono';

type Props = { children: ReactNode };
type State = { error: Error | null };

/**
 * 错误边界。
 *
 * ## 为什么需要
 *
 * 没有它时，任何一个渲染错误都会让界面**停在半途** —— 看上去就是「卡住了」，
 * 但没有提示，除了控制台之外查不到原因。有它至少能把错误显示出来，并给一个「重试」。
 *
 * ## 为什么不用 hook
 *
 * 这里刻意只依赖常量，不依赖 `useTheme()`：错误本身可能就出在主题上，
 * 兜底 UI 必须能用最少的依赖渲染出来。所以用固定浅色（黑白），不跟随明暗主题。
 *
 * 注意：错误边界抓不到事件回调与异步里的错误，只能兜住渲染期错误。
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[DAMN] 渲染出错：', error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    const c = MonoPalette.light;

    return (
      <View style={[styles.root, { backgroundColor: c.bg }]}>
        <Text style={[styles.title, { color: c.text }]}>这一页出错了</Text>
        <Text style={[styles.message, { color: c.danger }]} numberOfLines={8}>
          {error.message}
        </Text>
        <Pressable
          onPress={() => this.setState({ error: null })}
          accessibilityRole="button"
          style={({ pressed }) => [
            styles.button,
            { backgroundColor: pressed ? c.sub : c.strong },
          ]}>
          <Text style={[styles.buttonText, { color: c.onStrong }]}>重试</Text>
        </Pressable>
      </View>
    );
  }
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    alignItems: 'flex-start',
    justifyContent: 'center',
    gap: MonoSpace.four,
    padding: MonoSpace.six,
  },
  title: {
    fontSize: 24,
    lineHeight: 34,
    fontWeight: '700',
  },
  message: {
    fontSize: 14,
    lineHeight: 22,
    maxWidth: 480,
  },
  button: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: MonoSpace.six,
    borderRadius: MonoRadius.md,
  },
  buttonText: {
    fontSize: 16,
    fontWeight: '700',
  },
});
