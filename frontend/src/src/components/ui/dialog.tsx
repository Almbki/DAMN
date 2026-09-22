import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';

import { Button, IconButton, type ButtonVariant } from '@/components/ui/button';
import { Surface } from '@/components/ui/surface';
import { Line, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

export type DialogAction = {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
};

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
  if (!visible) return null;

  return (
    <Modal transparent visible animationType="fade" onRequestClose={onRequestClose}>
      <Pressable style={[styles.scrim, { backgroundColor: colors.scrim }]} onPress={closable ? onRequestClose : undefined}>
        <Pressable style={[styles.panelWrap, { maxWidth: width }]} onPress={() => undefined}>
          <Surface
            level="level4"
            radius="xl"
            style={{ maxHeight: Math.max(320, height * 0.9) }}>
            <View style={styles.head}>
              <Text style={[styles.title, { color: colors.ink }]}>{title}</Text>
              {closable && onRequestClose ? (
                <IconButton name="close" label="关闭" onPress={onRequestClose} size={40} />
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
                {actions.map((action) => (
                  <Button
                    key={action.label}
                    label={action.label}
                    variant={action.variant ?? 'text'}
                    disabled={action.disabled}
                    onPress={action.onPress}
                  />
                ))}
              </View>
            ) : null}
          </Surface>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  scrim: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: Space.lg,
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
