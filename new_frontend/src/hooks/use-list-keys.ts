import { useEffect, useRef } from 'react';
import { Platform } from 'react-native';

type ListKeyHandlers = {
  onPrev?: () => void;
  onNext?: () => void;
  onToggle?: () => void;
  onSkip?: () => void;
};

const EDITABLE_SELECTOR = [
  'input',
  'textarea',
  'select',
  'button',
  'a[href]',
  'summary',
  '[contenteditable="true"]',
  '[contenteditable=""]',
  '[contenteditable="plaintext-only"]',
].join(',');

const INTERACTIVE_ROLES = new Set([
  'button',
  'checkbox',
  'combobox',
  'listbox',
  'menuitem',
  'option',
  'radio',
  'searchbox',
  'slider',
  'spinbutton',
  'switch',
  'textbox',
]);

const INTERACTIVE_SELECTOR = [
  EDITABLE_SELECTOR,
  Array.from(INTERACTIVE_ROLES)
    .map((role) => `[role="${role}"]`)
    .join(','),
].join(',');

/** True for text entry and every control that already owns Space/arrow keys. */
function isInteractiveTarget(target: EventTarget | null): boolean {
  if (typeof HTMLElement === 'undefined' || !(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  if (target.closest(INTERACTIVE_SELECTOR)) return true;
  const role = target.getAttribute('role');
  return role != null && INTERACTIVE_ROLES.has(role);
}

/**
 * List navigation is only a shortcut for page-level focus. A focused control
 * (input, button, checkbox, link, contenteditable) keeps its own key behavior —
 * especially Space, which must press buttons instead of toggling a task.
 */
function isListScope(target: EventTarget | null): boolean {
  if (typeof HTMLElement === 'undefined' || !(target instanceof HTMLElement)) return false;
  if (target === document.body || target === document.documentElement) return true;
  return target.closest('[data-testid="todo-list"]') != null;
}

/**
 * Web-only roving list keys. Shortcuts are always a secondary path: every action
 * here is reachable by tap/click.
 */
export function useListKeys(handlers: ListKeyHandlers, enabled = true) {
  const handlersRef = useRef(handlers);

  useEffect(() => {
    handlersRef.current = handlers;
  }, [handlers]);

  useEffect(() => {
    if (Platform.OS !== 'web' || !enabled || typeof document === 'undefined') return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (isInteractiveTarget(event.target)) return;
      if (!isListScope(event.target)) return;

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
        case 'Spacebar':
          // Holding Space must not toggle repeatedly.
          if (event.repeat) {
            event.preventDefault();
            return;
          }
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
