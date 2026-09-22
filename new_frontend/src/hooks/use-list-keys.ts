import { useEffect, useRef } from 'react';
import { Platform } from 'react-native';

type ListKeyHandlers = {
  onPrev?: () => void;
  onNext?: () => void;
  onToggle?: () => void;
  onSkip?: () => void;
};

function isTextEntry(target: EventTarget | null): boolean {
  if (typeof HTMLElement === 'undefined' || !(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable;
}

/**
 * Web-only roving list keys. Shortcuts are always a secondary path: every action
 * here is reachable by tap/click. Keys are ignored while typing, so the add-goal
 * input and textareas are never hijacked.
 */
export function useListKeys(handlers: ListKeyHandlers, enabled = true) {
  const handlersRef = useRef(handlers);

  useEffect(() => {
    handlersRef.current = handlers;
  }, [handlers]);

  useEffect(() => {
    if (Platform.OS !== 'web' || !enabled || typeof document === 'undefined') return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (isTextEntry(event.target)) return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;

      switch (event.key) {
        case 'j':
        case 'ArrowDown':
          event.preventDefault();
          handlersRef.current.onNext?.();
          break;
        case 'k':
        case 'ArrowUp':
          event.preventDefault();
          handlersRef.current.onPrev?.();
          break;
        case ' ':
          event.preventDefault();
          handlersRef.current.onToggle?.();
          break;
        case 'l':
        case 'L':
          event.preventDefault();
          handlersRef.current.onSkip?.();
          break;
        default:
          break;
      }
    };

    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [enabled]);
}
