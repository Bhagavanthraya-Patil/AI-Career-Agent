import { type ReactNode } from 'react';
import { useTheme } from '@/hooks/use-theme';

interface ThemeProviderProps {
  children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  useTheme();
  return <>{children}</>;
}
