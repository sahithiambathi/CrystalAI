export default function ThemeToggle({ theme, onToggle }) {
  return (
    <button className="theme-toggle" type="button" onClick={onToggle} aria-label="Toggle theme">
      <span>{theme === "dark" ? "Light" : "Dark"} mode</span>
    </button>
  );
}
