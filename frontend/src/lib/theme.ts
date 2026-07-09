import * as React from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "wms_theme";

function systemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function getStoredTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return systemPrefersDark() ? "dark" : "light";
}

function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

/** Reads/writes the `dark` class + localStorage; index.html applies the initial theme pre-paint to avoid a flash. */
export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = React.useState<Theme>(() => getStoredTheme());

  React.useEffect(() => {
    applyTheme(theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggle = React.useCallback(() => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }, []);

  return [theme, toggle];
}
