import { useCallback, useState } from 'react';

/**
 * Hover + keyboard-focus state for a pressable element.
 *
 * Hover is a genuine capability check (touch laptops have both), so pages read
 * `hovered` to decide what to reveal — never `Platform.OS === 'web'`.
 */
export function useInteraction() {
  const [focused, setFocused] = useState(false);
  const [hovered, setHovered] = useState(false);

  const onFocus = useCallback(() => setFocused(true), []);
  const onBlur = useCallback(() => setFocused(false), []);
  const onHoverIn = useCallback(() => setHovered(true), []);
  const onHoverOut = useCallback(() => setHovered(false), []);

  return {
    focused,
    hovered,
    handlers: { onFocus, onBlur, onHoverIn, onHoverOut },
  };
}
