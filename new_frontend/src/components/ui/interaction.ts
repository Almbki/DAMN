import { useCallback, useEffect, useState } from 'react';
import { Platform } from 'react-native';

/**
 * Hover + keyboard-focus state for a pressable element.
 *
 * Hover is a genuine capability check (touch laptops have both), so pages read
 * `hovered` to decide what to reveal — never `Platform.OS === 'web'`.
 *
 * `focused` means **focus-visible**: it is only true when focus arrived from the
 * keyboard. A mouse/touch click focuses the element too, but we must not leave a
 * persistent focus ring behind, so we track the last input modality on web.
 */
const isWeb = Platform.OS === 'web';

let keyboardModality = false;
let listening = false;

function ensureModalityListeners() {
  if (!isWeb || listening || typeof document === 'undefined') return;
  listening = true;
  // Capture phase so the flag is set before the element's focus handler runs.
  document.addEventListener('keydown', () => {
    keyboardModality = true;
  }, true);
  document.addEventListener('pointerdown', () => {
    keyboardModality = false;
  }, true);
  document.addEventListener('mousedown', () => {
    keyboardModality = false;
  }, true);
}

export function useInteraction() {
  const [focused, setFocused] = useState(false);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    ensureModalityListeners();
  }, []);

  const onFocus = useCallback(() => {
    // Native has no pointer-vs-keyboard distinction; always show the ring.
    setFocused(isWeb ? keyboardModality : true);
  }, []);
  const onBlur = useCallback(() => setFocused(false), []);
  const onHoverIn = useCallback(() => setHovered(true), []);
  const onHoverOut = useCallback(() => setHovered(false), []);

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
