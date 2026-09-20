/**
 * 极简黑白的通用件。
 *
 * 这一层是新前端的积木：卡片、按钮、输入、勾选框、档位选择、标签、页面壳。
 * 颜色一律走 `useMono()`，所以浅色 / 深色自动切换，页面里不写颜色字面量。
 *
 * 视觉规矩（照模板）：
 * - 结构靠 1px 边框与灰度，**不用阴影**；
 * - 圆角只用 4 / 8；
 * - 交互态用灰度底（hover / active），不换色相。
 */

import { useState, type ReactNode } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type TextProps,
  type TextInputProps,
  type TextStyle,
  type ViewStyle,
} from 'react-native';

import {
  MonoFonts,
  MonoRadius,
  MonoSpace,
  MonoType,
  type MonoColorName,
  type MonoTypeName,
} from '@/constants/mono';
import { useMono } from '@/hooks/use-mono';

/* ------------------------------------------------------------------ 文本 */

export type MonoTextProps = TextProps & {
  type?: MonoTypeName;
  color?: MonoColorName;
};

export function MonoText({
  type = 'body',
  color = 'text',
  style,
  children,
  ...rest
}: MonoTextProps) {
  const c = useMono();
  return (
    <Text style={[{ color: c[color], fontFamily: MonoFonts.sans }, MonoType[type], style]} {...rest}>
      {children}
    </Text>
  );
}

/** 发丝线。 */
export function MonoRule({ style }: { style?: StyleProp<ViewStyle> }) {
  const c = useMono();
  return <View style={[styles.rule, { backgroundColor: c.border }, style]} />;
}

/* ------------------------------------------------------------------ 卡片 */

export function Card({
  title,
  children,
  style,
}: {
  title?: string;
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  const c = useMono();
  return (
    <View style={[styles.card, { borderColor: c.border, backgroundColor: c.bg }, style]}>
      {title ? (
        <View style={[styles.cardTitle, { borderBottomColor: c.border }]}>
          <MonoText type="title">{title}</MonoText>
        </View>
      ) : null}
      <View style={styles.cardBody}>{children}</View>
    </View>
  );
}

/* ------------------------------------------------------------------ 按钮 */

export type BtnVariant = 'default' | 'primary';

export function Btn({
  label,
  onPress,
  variant = 'default',
  disabled = false,
  full = false,
  style,
}: {
  label: string;
  onPress?: () => void;
  variant?: BtnVariant;
  disabled?: boolean;
  full?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const c = useMono();
  const [pressed, setPressed] = useState(false);
  const primary = variant === 'primary';

  return (
    <Pressable
      onPress={disabled ? undefined : onPress}
      onPressIn={() => setPressed(true)}
      onPressOut={() => setPressed(false)}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      style={[
        styles.btn,
        {
          borderColor: primary ? c.strong : c.border,
          backgroundColor: primary ? c.strong : c.bg,
        },
        pressed && !disabled && { backgroundColor: primary ? c.strong : c.hover, opacity: primary ? 0.9 : 1 },
        disabled && styles.disabled,
        full && styles.btnFull,
        style,
      ]}>
      <MonoText type="bodyStrong" style={{ color: primary ? c.onStrong : c.text }}>
        {label}
      </MonoText>
    </Pressable>
  );
}

/* ------------------------------------------------------------------ 表单 */

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <View style={styles.field}>
      <View style={styles.fieldHead}>
        <MonoText type="label" color="sub">
          {label}
        </MonoText>
        {hint ? (
          <MonoText type="caption" color="faint">
            {hint}
          </MonoText>
        ) : null}
      </View>
      {children}
    </View>
  );
}

export function MonoInput({ style, onFocus, onBlur, ...rest }: TextInputProps) {
  const c = useMono();
  const [focused, setFocused] = useState(false);

  return (
    <TextInput
      {...rest}
      placeholderTextColor={rest.placeholderTextColor ?? c.faint}
      onFocus={(event) => {
        setFocused(true);
        onFocus?.(event);
      }}
      onBlur={(event) => {
        setFocused(false);
        onBlur?.(event);
      }}
      style={[
        styles.input,
        {
          color: c.text,
          borderColor: focused ? c.strong : c.border,
          backgroundColor: c.bg,
        },
        style,
      ]}
    />
  );
}

/* ------------------------------------------------------------------ 档位 */

/**
 * 四档选择器（精力 / 压力 / 外观）。
 * 选中档用实心重色表达，未选中用边框 —— 颜色不单独表意，每档都有文字。
 */
export function LevelPicker({
  ask,
  options,
  value,
  onChange,
}: {
  ask: string;
  options: readonly string[];
  value: number | null;
  onChange: (index: number) => void;
}) {
  const c = useMono();

  return (
    <View style={styles.levelRoot}>
      <MonoText type="body">{ask}</MonoText>
      <View style={[styles.levelRow, { borderColor: c.border }]}>
        {options.map((option, index) => {
          const selected = value === index;
          return (
            <Pressable
              key={option}
              onPress={() => onChange(index)}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              accessibilityLabel={option}
              style={[
                styles.levelCell,
                index > 0 && { borderLeftWidth: StyleSheet.hairlineWidth, borderLeftColor: c.border },
                selected && { backgroundColor: c.strong },
              ]}>
              <MonoText type="caption" style={{ color: selected ? c.onStrong : c.sub }}>
                {option}
              </MonoText>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

/* ---------------------------------------------------------------- 勾选框 */

export function Checkbox({ checked, disabled }: { checked: boolean; disabled?: boolean }) {
  const c = useMono();
  return (
    <View
      style={[
        styles.checkbox,
        {
          borderColor: c.strong,
          backgroundColor: checked ? c.strong : 'transparent',
          opacity: disabled ? 0.45 : 1,
        },
      ]}>
      {checked ? (
        <Text style={{ color: c.onStrong, fontSize: 13, lineHeight: 16, fontWeight: '700' }}>✓</Text>
      ) : null}
    </View>
  );
}

/** 小标签。`tone="strong"` 给当前项。 */
export function Tag({ label, tone = 'default' }: { label: string; tone?: 'default' | 'strong' }) {
  const c = useMono();
  return (
    <View
      style={[
        styles.tag,
        { borderColor: tone === 'strong' ? c.strong : c.border },
        tone === 'strong' && { backgroundColor: c.strong },
      ]}>
      <MonoText type="micro" style={{ color: tone === 'strong' ? c.onStrong : c.sub }}>
        {label}
      </MonoText>
    </View>
  );
}

/* ---------------------------------------------------------------- 页面壳 */

/** 可滚动页面壳：内容居中、最大 800px、四周留白。 */
export function Screen({ children }: { children: ReactNode }) {
  const c = useMono();
  return (
    <ScrollView
      style={[styles.screen, { backgroundColor: c.bg }]}
      contentContainerStyle={styles.screenScroll}
      showsVerticalScrollIndicator={false}>
      <View style={styles.screenInner}>{children}</View>
    </ScrollView>
  );
}

/* ---------------------------------------------------------------- 样式 */

const styles = StyleSheet.create({
  rule: { height: StyleSheet.hairlineWidth, width: '100%' },

  card: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: MonoRadius.md,
    overflow: 'hidden',
  },
  cardTitle: {
    paddingHorizontal: MonoSpace.five,
    paddingVertical: MonoSpace.four,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  cardBody: {
    padding: MonoSpace.five,
    gap: MonoSpace.four,
  },

  btn: {
    minHeight: 44,
    paddingHorizontal: MonoSpace.four,
    borderRadius: MonoRadius.sm,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  btnFull: { width: '100%' },
  disabled: { opacity: 0.45 },

  field: { gap: MonoSpace.two },
  fieldHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: MonoSpace.three,
  },
  input: {
    width: '100%',
    minHeight: 44,
    paddingHorizontal: MonoSpace.three,
    paddingVertical: MonoSpace.two,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: MonoRadius.sm,
    fontSize: 14,
    lineHeight: 20,
  },

  levelRoot: { gap: MonoSpace.three },
  levelRow: {
    flexDirection: 'row',
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: MonoRadius.sm,
    overflow: 'hidden',
  },
  levelCell: {
    flex: 1,
    minHeight: 40,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: MonoSpace.one,
  },

  checkbox: {
    width: 20,
    height: 20,
    borderWidth: 1,
    borderRadius: MonoRadius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },

  tag: {
    paddingHorizontal: MonoSpace.two,
    paddingVertical: 1,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: MonoRadius.full,
  },

  screen: { flex: 1 },
  screenScroll: {
    flexGrow: 1,
    alignItems: 'center',
    paddingHorizontal: MonoSpace.four,
    paddingVertical: MonoSpace.five,
  },
  screenInner: {
    width: '100%',
    maxWidth: 800,
    gap: MonoSpace.four,
  },
});
