import { useEffect } from 'react';
import { useThemeStore } from '@/store/theme-store';

export function useTheme() {
  const { theme, setTheme, getEffectiveTheme } = useThemeStore();

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', getEffectiveTheme() === 'dark');
  }, [theme, getEffectiveTheme]);

  useEffect(() => {
    if (theme !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      document.documentElement.classList.toggle('dark', mediaQuery.matches);
    };
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [theme]);

  return { theme, setTheme, effectiveTheme: getEffectiveTheme() };
}
