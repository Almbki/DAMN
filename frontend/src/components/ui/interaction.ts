import { useCallback, useState } from 'react';

import { useInputModality } from '@/hooks/use-input-modality';

/**
 * Hover + keyboard-focus state for a pressable element.
 *
 * `focused` is deliberately "keyboard focus only": a mouse click focuses the
 * element but must not paint a ring (that box is what the user called ugly).
 * The raw focus bit is still tracked, it is just combined with the last input
 * modality before it is exposed.
 *
 * Hover is a genuine capability check (touch laptops have both), so pages read
 * `hovered` to decide what to reveal — never `Platform.OS === 'web'`.
 */
export function useInteraction() {
  const modality = useInputModality();
  const [elementFocused, setElementFocused] = useState(false);
  const [hovered, setHovered] = useState(false);

  const onFocus = useCallback(() => setElementFocused(true), []);
  const onBlur = useCallback(() => setElementFocused(false), []);
  const onHoverIn = useCallback(() => setHovered(true), []);
  const onHoverOut = useCallback(() => setHovered(false), []);

  // Only the keyboard gets a ring; a pointer press never does.
  const focused = elementFocused && modality === 'keyboard';

  return {
    focused,
    hovered,
    onFocus,
    onBlur,
    onHoverIn,
    onHoverOut,
    handlers: { onFocus, onBlur, onHoverIn, onHoverOut },
  };
}
