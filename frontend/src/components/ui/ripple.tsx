import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Animated,
  Easing as RNEasing,
  StyleSheet,
  View,
  type GestureResponderEvent,
  type LayoutChangeEvent,
} from 'react-native';

import { Motion, Ripple as RippleTokens } from '@/constants/tokens';
import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { useTheme } from '@/state/theme';

/**
 * Material press ripple, shared by every pressable surface.
 *
 * A circle is spawned at the touch point and grows to 2.2× while fading from
 * 18% to nothing, on RN's `Animated` (transform + opacity only). Cross-platform:
 * the same code runs on web and native — only the driver differs.
 *
 * Usage:
 *   const ripple = useRipple();
 *   <Pressable onLayout={ripple.onLayout} onPressIn={ripple.onPressIn}>
 *     {ripple.node}
 *     ...
 *   </Pressable>
 *
 * The parent pressable must clip (`overflow: 'hidden'`) and be positioned, which
 * every RN view already is. Reduced motion skips the ripple entirely.
 */

type Bubble = {
  id: number;
  /** Press point, relative to the pressable. */
  x: number;
  y: number;
  /** Base diameter, the surface diagonal, so scale 1 already covers a corner. */
  size: number;
};

export function useRipple(color?: string) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const sizeRef = useRef({ width: 0, height: 0 });
  const idRef = useRef(0);

  const onLayout = useCallback((event: LayoutChangeEvent) => {
    const { width, height } = event.nativeEvent.layout;
    sizeRef.current = { width, height };
  }, []);

  const handleDone = useCallback((id: number) => {
    setBubbles((prev) => prev.filter((bubble) => bubble.id !== id));
  }, []);

  const onPressIn = useCallback(
    (event: GestureResponderEvent) => {
      if (reduced) return;
      const { width, height } = sizeRef.current;
      const diagonal = Math.hypot(width, height) || 24;
      const rawX = event.nativeEvent.locationX;
      const rawY = event.nativeEvent.locationY;
      idRef.current += 1;
      setBubbles((prev) => [
        ...prev,
        {
          id: idRef.current,
          x: Number.isFinite(rawX) ? rawX : width / 2,
          y: Number.isFinite(rawY) ? rawY : height / 2,
          size: diagonal,
        },
      ]);
    },
    [reduced],
  );

  const node = (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      {bubbles.map((bubble) => (
        <RippleBubble
          key={bubble.id}
          {...bubble}
          color={color ?? colors.ripple}
          onDone={handleDone}
        />
      ))}
    </View>
  );

  return { onLayout, onPressIn, node };
}

function RippleBubble({
  id,
  x,
  y,
  size,
  color,
  onDone,
}: Bubble & { color: string; onDone: (id: number) => void }) {
  // A stable animated value read during render; `useState`'s lazy initializer
  // replaces `useRef(...).current`, which React no longer allows to be read in
  // render.
  const [progress] = useState(() => new Animated.Value(0));

  useEffect(() => {
    const animation = Animated.timing(progress, {
      toValue: 1,
      duration: RippleTokens.duration,
      // Decelerate: fast out of the touch, easing to a stop.
      easing: RNEasing.bezier(0.05, 0.7, 0.1, 1),
      useNativeDriver: Motion.nativeDriver,
    });
    animation.start(({ finished }) => {
      if (finished) onDone(id);
    });
    return () => animation.stop();
  }, [id, onDone, progress]);

  const diameter = size;

  return (
    <Animated.View
      style={{
        position: 'absolute',
        left: x - diameter / 2,
        top: y - diameter / 2,
        width: diameter,
        height: diameter,
        borderRadius: diameter / 2,
        backgroundColor: color,
        opacity: progress.interpolate({
          inputRange: [0, 1],
          outputRange: [RippleTokens.opacity, 0],
        }),
        transform: [
          {
            scale: progress.interpolate({
              inputRange: [0, 1],
              outputRange: [0, RippleTokens.scale],
            }),
          },
        ],
      }}
    />
  );
}
