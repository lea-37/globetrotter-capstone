function applyStoredTheme() {
  const saved = localStorage.getItem("bastos_theme") || "light";
  if (saved === "dark") document.documentElement.setAttribute("data-theme", "dark");
}
applyStoredTheme();

function toggleTheme() {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  if (isDark) {
    document.documentElement.removeAttribute("data-theme");
    localStorage.setItem("bastos_theme", "light");
  } else {
    document.documentElement.setAttribute("data-theme", "dark");
    localStorage.setItem("bastos_theme", "dark");
  }
  updateThemeIcon();
}

function updateThemeIcon() {
  const btn = document.getElementById("themeToggle");
  if (!btn) return;
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  btn.textContent = isDark ? "☀️" : "🌙";
}

document.addEventListener("DOMContentLoaded", updateThemeIcon);
