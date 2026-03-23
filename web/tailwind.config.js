/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        page: "rgb(var(--c-page) / <alpha-value>)",
        surface: "rgb(var(--c-surface) / <alpha-value>)",
        "surface-alt": "rgb(var(--c-surface-alt) / <alpha-value>)",
        field: "rgb(var(--c-field) / <alpha-value>)",
        edge: "rgb(var(--c-edge) / <alpha-value>)",
        "edge-soft": "rgb(var(--c-edge-soft) / <alpha-value>)",
        "edge-row": "rgb(var(--c-edge-row) / <alpha-value>)",
        content: "rgb(var(--c-content) / <alpha-value>)",
        "content-secondary": "rgb(var(--c-content-secondary) / <alpha-value>)",
        "content-muted": "rgb(var(--c-content-muted) / <alpha-value>)",
        "content-faint": "rgb(var(--c-content-faint) / <alpha-value>)",
        overlay: "rgb(var(--c-overlay) / <alpha-value>)",
      },
    },
  },
  plugins: [],
};
