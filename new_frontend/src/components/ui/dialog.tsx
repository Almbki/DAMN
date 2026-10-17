import { Children, isValidElement } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Button, IconButton, type ButtonVariant } from '@/components/ui/button';
import { Surface } from '@/components/ui/surface';
import { Line, Space, Type } from '@/constants/tokens';
import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { useTheme } from '@/state/theme';

export type DialogAction = {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
};

/**
 * If the dialog content already asks for focus (a text field with
 * `autoFocus`), leave it alone instead of pulling focus to an action button.
 */
function hasAutoFocusChild(node: React.ReactNode): boolean {
  let found = false;
  Children.forEach(node, (child) => {
    if (found || !isValidElement(child)) return;
    const props = child.props as { autoFocus?: boolean; children?: React.ReactNode };
    if (props.autoFocus) {
      found = true;
      return;
    }
    if (props.children) found = hasAutoFocusChild(props.children);
  });
  return found;
}

/** Material 3 basic dialog: scrim, elevated container, left-aligned copy. */
export function Dialog({
  visible,
  title,
  description,
  children,
  actions = [],
  onRequestClose,
  closable = true,
  width = 440,
}: {
  visible: boolean;
  title: string;
  description?: string;
  children?: React.ReactNode;
  actions?: DialogAction[];
  onRequestClose?: () => void;
  closable?: boolean;
  width?: number;
}) {
  const { colors } = useTheme();
  const { height } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const reducedMotion = useReducedMotion();
  if (!visible) return null;

  // Start on the close button (the safest neutral control), unless the content
  // already owns focus. A dialog without a close button falls back to its first
  // enabled action.
  const contentAutoFocus = hasAutoFocusChild(children);
  const firstEnabledAction = actions.findIndex((action) => !action.disabled);
  const focusClose = closable && onRequestClose != null;
  const focusAction = focusClose ? -1 : firstEnabledAction;

  return (
    <Modal
      transparent
      visible
      animationType={reducedMotion ? 'none' : 'fade'}
      onRequestClose={onRequestClose}
      statusBarTranslucent>
      <View
        accessibilityViewIsModal
        style={[
          styles.scrim,
          {
            backgroundColor: colors.scrim,
            paddingTop: Math.max(Space.lg, insets.top),
            paddingBottom: Math.max(Space.lg, insets.bottom),
            paddingLeft: Math.max(Space.lg, insets.left),
            paddingRight: Math.max(Space.lg, insets.right),
          },
        ]}>
        <Pressable
          accessible={false}
          style={StyleSheet.absoluteFill}
          onPress={closable ? onRequestClose : undefined}
        />

        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.keyboard}
          pointerEvents="box-none">
          <Pressable
            style={[styles.panelWrap, { maxWidth: width }]}
            onPress={() => undefined}
            accessible={false}>
            <Surface
              level="level4"
              radius="xl"
              style={{ maxHeight: Math.max(320, height * 0.9) }}>
              <View style={styles.head}>
                <Text accessibilityRole="header" style={[styles.title, { color: colors.ink }]}>
                  {title}
                </Text>
                {closable && onRequestClose ? (
                  <IconButton
                    name="close"
                    label="关闭"
                    onPress={onRequestClose}
                    size={44}
                    autoFocus={!contentAutoFocus && focusClose}
                  />
                ) : null}
              </View>

              {description ? (
                <Text style={[styles.description, { color: colors.inkMuted }]}>{description}</Text>
              ) : null}

              {children ? (
                <ScrollView
                  style={styles.body}
                  contentContainerStyle={styles.bodyContent}
                  keyboardShouldPersistTaps="handled">
                  {children}
                </ScrollView>
              ) : null}

              {actions.length > 0 ? (
                <View style={[styles.actions, { borderTopColor: colors.line }]}>
                  {actions.map((action, index) => (
                    <Button
                      key={action.label}
                      label={action.label}
                      variant={action.variant ?? 'text'}
                      disabled={action.disabled}
                      autoFocus={!contentAutoFocus && index === focusAction}
                      onPress={action.onPress}
                    />
                  ))}
                </View>
              ) : null}
            </Surface>
          </Pressable>
        </KeyboardAvoidingView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  scrim: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  keyboard: {
    width: '100%',
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  panelWrap: {
    width: '100%',
    maxHeight: '92%',
  },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
    paddingLeft: Space.xl,
    paddingRight: Space.sm,
    paddingTop: Space.sm,
  },
  title: {
    flex: 1,
    fontSize: Type.headlineSmall,
    lineHeight: Line.normal * Type.headlineSmall,
    fontWeight: '500',
  },
  description: {
    paddingHorizontal: Space.xl,
    paddingTop: Space.sm,
    fontSize: Type.bodyMedium,
    lineHeight: Line.relaxed * Type.bodyMedium,
  },
  body: {
    flexShrink: 1,
  },
  bodyContent: {
    paddingHorizontal: Space.xl,
    paddingTop: Space.lg,
    gap: Space.lg,
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    flexWrap: 'wrap',
    gap: Space.sm,
    borderTopWidth: 1,
    marginTop: Space.xl,
    padding: Space.md,
  },
});
