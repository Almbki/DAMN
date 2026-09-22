import { useState } from 'react';
import { StyleSheet, Text, TextInput, View, type TextInputProps } from 'react-native';

import { Line, Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/**
 * Material 3 outlined text field with a floating label. The label always rests
 * on the top border (no animation), which keeps it legible and stable; the
 * focus ring is the primary colour.
 */
export function TextField({
  label,
  value,
  onChangeText,
  placeholder,
  multiline = false,
  autoFocus = false,
  error,
  keyboardType,
  testID,
  background,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder?: string;
  multiline?: boolean;
  autoFocus?: boolean;
  error?: string | null;
  keyboardType?: TextInputProps['keyboardType'];
  testID?: string;
  /** Surface colour the field sits on, used to notch the floating label. */
  background?: string;
}) {
  const { colors } = useTheme();
  const [focused, setFocused] = useState(false);
  const borderColor = error ? colors.error : focused ? colors.primary : colors.outline;

  return (
    <View style={styles.wrap}>
      <View
        style={[
          styles.box,
          multiline && styles.boxMultiline,
          {
            borderColor,
            backgroundColor: background ?? colors.surfaceContainerLowest,
            boxShadow: focused ? `0 0 0 1px ${borderColor}` : undefined,
          },
        ]}>
        <Text
          style={[
            styles.floating,
            {
              color: error ? colors.error : focused ? colors.primary : colors.inkMuted,
              backgroundColor: background ?? colors.surfaceContainerLowest,
            },
          ]}>
          {label}
        </Text>
        <TextInput
          value={value}
          onChangeText={onChangeText}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          placeholderTextColor={colors.inkFaint}
          multiline={multiline}
          autoFocus={autoFocus}
          keyboardType={keyboardType}
          accessibilityLabel={label}
          testID={testID}
          style={[styles.input, multiline && styles.inputMultiline, { color: colors.ink }]}
        />
      </View>
      {error ? <Text style={[styles.error, { color: colors.error }]}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: Space.xs,
  },
  box: {
    borderWidth: 1,
    borderRadius: Radius.xs,
    minHeight: 56,
    justifyContent: 'center',
  },
  boxMultiline: {
    minHeight: 104,
  },
  floating: {
    position: 'absolute',
    top: -9,
    left: 12,
    paddingHorizontal: 4,
    fontSize: Type.labelMedium,
  },
  input: {
    paddingHorizontal: 14,
    paddingTop: 14,
    paddingBottom: 8,
    fontSize: Type.bodyLarge,
  },
  inputMultiline: {
    paddingTop: 20,
    paddingBottom: 12,
    minHeight: 104,
    textAlignVertical: 'top',
  },
  error: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.normal,
  },
});
