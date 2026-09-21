import { useSyncExternalStore } from 'react';
import { Platform } from 'react-native';

/**
 * Tracks how the user last interacted, so the focus ring can be shown for
 * keyboard navigation and hidden for a mouse/touch press.
 *
 * The browser draws its own default outline on click, which is the ugly box the
 * user complained about; we suppress that in `global.css` and paint our own ring
 * only when the last input was the keyboard. This is the standard
 * `:focus-visible` behaviour, implemented by hand because the ring has to look
 * and behave identically on all three platforms.
 *
 * All DOM access lives here (never in a page): native has no document, so the
 * modality simply stays on its platform default.
 */

export type InputModality = 'pointer' | 'keyboard';

const isWeb = Platform.OS === 'web';

/** Web users mostly click; native has no pointer, so focus there means keyboard. */
let modality: InputModality = isWeb ? 'pointer' : 'keyboard';

const listeners = new Set<() => void>();
let attached = false;

/** Only navigation keys flip to keyboard mode; typing does not. */
const KEYBOARD_NAV_KEYS = new Set([
  'Tab',
  'ArrowUp',
  'ArrowDown',
  'ArrowLeft',
  'ArrowRight',
  'Home',
  'End',
  'PageUp',
  'PageDown',
]);

function emit() {
  listeners.forEach((listener) => listener());
}

function setModality(next: InputModality) {
  if (modality === next) return;
  modality = next;
  emit();
}

function handlePointerDown() {
  setModality('pointer');
}

function handleKeyDown(event: KeyboardEvent) {
  if (KEYBOARD_NAV_KEYS.has(event.key)) setModality('keyboard');
}

function ensureListeners() {
  if (attached || !isWeb || typeof document === 'undefined') return;
  attached = true;
  // Capture phase: the modality is decided before the browser moves focus.
  document.addEventListener('pointerdown', handlePointerDown, true);
  document.addEventListener('keydown', handleKeyDown, true);
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  ensureListeners();
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): InputModality {
  return modality;
}

/** Static render has no interaction yet; assume pointer so no ring is painted. */
function getServerSnapshot(): InputModality {
  return 'pointer';
}

export function useInputModality(): InputModality {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
