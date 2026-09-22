import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';

import { IconButton } from '@/components/ui/button';
import { Surface } from '@/components/ui/surface';
import { Line, Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/**
 * Material 3 modal bottom sheet. The header stays put and the body scrolls, so
 * long content (feedback, decomposition, change log) never traps the actions.
 */
export function BottomSheet({
  visible,
  title,
  subtitle,
  children,
  footer,
  onClose,
  maxWidth = 640,
}: {
  visible: boolean;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  onClose: () => void;
  maxWidth?: number;
}) {
  const { colors } = useTheme();
  const { height } = useWindowDimensions();
  if (!visible) return null;

  return (
    <Modal transparent visible animationType="slide" onRequestClose={onClose}>
      <View style={styles.root}>
        <Pressable
          accessibilityLabel="关闭"
          style={[StyleSheet.absoluteFill, { backgroundColor: colors.scrim }]}
          onPress={onClose}
        />
        <Surface
          level="level3"
          radius="xl"
          tone="lowest"
          style={[styles.sheet, { maxWidth, maxHeight: Math.max(280, height * 0.88) }]}>
          <View style={[styles.handle, { backgroundColor: colors.outlineVariant }]} />
          <View style={styles.header}>
            <View style={styles.headerText}>
              <Text style={[styles.title, { color: colors.ink }]}>{title}</Text>
              {subtitle ? (
                <Text style={[styles.subtitle, { color: colors.inkMuted }]}>{subtitle}</Text>
              ) : null}
            </View>
            <IconButton name="close" label="关闭" onPress={onClose} />
          </View>

          <ScrollView
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            keyboardShouldPersistTaps="handled">
            {children}
          </ScrollView>

          {footer ? (
            <View style={[styles.footer, { borderTopColor: colors.line }]}>{footer}</View>
          ) : null}
        </Surface>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  sheet: {
    width: '100%',
    borderBottomLeftRadius: 0,
    borderBottomRightRadius: 0,
    paddingTop: Space.sm,
  },
  handle: {
    width: 32,
    height: 4,
    borderRadius: Radius.pill,
    alignSelf: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Space.md,
    paddingLeft: Space.xl,
    paddingRight: Space.sm,
    paddingTop: Space.md,
    paddingBottom: Space.sm,
  },
  headerText: {
    flex: 1,
    gap: Space.xs,
  },
  title: {
    fontSize: Type.titleLarge,
    fontWeight: '600',
  },
  subtitle: {
    fontSize: Type.bodyMedium,
    lineHeight: Line.normal * Type.bodyMedium,
  },
  scroll: {
    flexShrink: 1,
  },
  scrollContent: {
    paddingHorizontal: Space.xl,
    paddingTop: Space.sm,
    paddingBottom: Space.xl,
    gap: Space.lg,
  },
  footer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'flex-end',
    gap: Space.sm,
    borderTopWidth: 1,
    padding: Space.lg,
  },
});
