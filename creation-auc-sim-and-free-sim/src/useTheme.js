// src/hooks/useTheme.js
import { useEffect, useState } from "react";

export function useTheme() {
  const [theme, setTheme] = useState("light");

  useEffect(() => {
    const storedTheme = localStorage.getItem("theme");
    if (
      storedTheme === "dark" ||
      (!storedTheme && window.matchMedia("(prefers-color-scheme: dark)").matches)
    ) {
      setTheme("dark");
    }
  }, []);

  useEffect(() => {
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  return [theme, setTheme];
}