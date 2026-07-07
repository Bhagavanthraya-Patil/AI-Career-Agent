import { create } from "zustand";

export type Theme = "light" | "dark" | "system";

interface ThemeStore {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  getEffectiveTheme: () => "light" | "dark";
}

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  const resolved = theme === "system" ? getSystemTheme() : theme;
  root.classList.toggle("dark", resolved === "dark");
}

export const useThemeStore = create<ThemeStore>()((set, get) => ({
  theme: "system",
  setTheme: (theme) => {
    applyTheme(theme);
    set({ theme });
  },
  getEffectiveTheme: () => {
    const { theme } = get();
    return theme === "system" ? getSystemTheme() : theme;
  },
}));

if (typeof window !== "undefined") {
  applyTheme("system");
  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", () => {
      const store = useThemeStore.getState();
      if (store.theme === "system") {
        applyTheme("system");
      }
    });
}
