import { useState } from 'react';
import { StyleSheet, Text, TextInput, View, type TextInputProps } from 'react-native';

import { Line, Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

type Props = {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder?: string;
  multiline?: boolean;
  autoFocus?: boolean;
  error?: string | null;
  keyboardType?: TextInputProps['keyboardType'];
  testID?: string;
};

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
}: Props) {
  const { colors } = useTheme();
  const [focused, setFocused] = useState(false);

  return (
    <View style={styles.wrap}>
      <Text style={[styles.label, { color: colors.inkMuted }]}>{label}</Text>
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
        style={[
          styles.input,
          multiline ? styles.multiline : null,
          {
            color: colors.ink,
            borderColor: error ? colors.ink : focused ? colors.accent : colors.line,
            backgroundColor: colors.paper,
          },
        ]}
      />
      {error ? <Text style={[styles.error, { color: colors.ink }]}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: Space.sm,
  },
  label: {
    fontSize: Type.small,
  },
  input: {
    minHeight: 44,
    borderWidth: 2,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.md,
    fontSize: Type.body,
  },
  multiline: {
    minHeight: 84,
    paddingTop: Space.md,
    textAlignVertical: 'top',
  },
  error: {
    fontSize: Type.small,
    lineHeight: Type.small * Line.normal,
  },
});
