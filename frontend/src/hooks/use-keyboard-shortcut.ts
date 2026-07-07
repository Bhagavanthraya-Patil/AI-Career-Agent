import { useEffect } from 'react';

interface Shortcut {
  key: string;
  meta?: boolean;
  ctrl?: boolean;
  handler: () => void;
}

export function useKeyboardShortcut(shortcuts: Shortcut[]): void {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const metaMatch = shortcut.meta ? event.metaKey : true;
        const ctrlMatch = shortcut.ctrl ? event.ctrlKey : true;

        if (metaMatch && ctrlMatch && event.key.toLowerCase() === shortcut.key.toLowerCase()) {
          event.preventDefault();
          shortcut.handler();
          return;
        }
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [shortcuts]);
}
