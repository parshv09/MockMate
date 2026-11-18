/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--color-background)",
        surface: {
          DEFAULT: "var(--color-surface)",
          subtle: "var(--color-surface-subtle)",
          booth: "var(--color-surface-booth)",
          "booth-elevated": "var(--color-surface-booth-elevated)",
        },
        foreground: {
          DEFAULT: "var(--color-foreground)",
          secondary: "var(--color-foreground-secondary)",
          muted: "var(--color-muted-foreground)",
          booth: "var(--color-booth-foreground)",
        },
        primary: {
          DEFAULT: "var(--color-primary)",
          hover: "var(--color-primary-hover)",
          subtle: "var(--color-primary-subtle)",
          foreground: "var(--color-on-primary)",
        },
        secondary: {
          DEFAULT: "var(--color-secondary)",
          subtle: "var(--color-secondary-subtle)",
          foreground: "var(--color-on-secondary)",
        },
        success: {
          DEFAULT: "var(--color-success)",
          bg: "var(--color-success-bg)",
        },
        warning: {
          DEFAULT: "var(--color-warning)",
          bg: "var(--color-warning-bg)",
        },
        destructive: {
          DEFAULT: "var(--color-destructive)",
          bg: "var(--color-destructive-bg)",
          foreground: "var(--color-on-destructive)",
        },
        border: {
          DEFAULT: "var(--color-border)",
          strong: "var(--color-border-strong)",
        },
        ring: "var(--color-ring)",
      },
      fontFamily: {
        sans: ["'Plus Jakarta Sans'", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        display: ["'Plus Jakarta Sans'", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      boxShadow: {
        none: "none",
        xs: "var(--shadow-xs)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
      },
      maxWidth: {
        studio: "1200px",
      },
    },
  },
  plugins: [],
};

