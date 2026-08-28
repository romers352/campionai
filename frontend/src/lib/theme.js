// Tiny theme system: "dark" (default, obsidian) or "light" (warm cream).
const KEY = "campion_theme";

export function getTheme() {
  return localStorage.getItem(KEY) || "dark";
}

export function applyTheme(theme) {
  const el = document.documentElement;
  if (theme === "light") {
    el.classList.add("light");
    el.classList.remove("dark");
  } else {
    el.classList.remove("light");
    el.classList.add("dark");
  }
  localStorage.setItem(KEY, theme);
}

export function toggleTheme() {
  const next = getTheme() === "light" ? "dark" : "light";
  applyTheme(next);
  return next;
}

// Apply immediately on import so there's no flash of the wrong theme.
applyTheme(getTheme());
