import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: "var(--color-brand-blue)",
          blueMid: "var(--color-brand-blue-mid)",
          blueTint: "var(--color-brand-blue-tint)",
          gold: "var(--color-brand-gold)",
          goldTint: "var(--color-brand-gold-tint)",
          goldDim: "var(--color-brand-gold-dim)",
        },
        surface: {
          page: "var(--color-surface-page)",
          white: "var(--color-surface-white)",
        },
        border: {
          default: "var(--color-border-default)",
        },
        ink: {
          primary: "var(--color-ink-primary)",
          2: "var(--color-ink-2)",
          3: "var(--color-ink-3)",
          4: "var(--color-ink-4)",
        },
        status: {
          openBg: "var(--color-status-open-bg)",
          openText: "var(--color-status-open-text)",
          warningBg: "var(--color-status-warning-bg)",
          warningText: "var(--color-status-warning-text)",
          errorBg: "var(--color-status-error-bg)",
          errorText: "var(--color-status-error-text)",
          infoBg: "var(--color-status-info-bg)",
          infoText: "var(--color-status-info-text)",
        },
      },
      fontFamily: {
        sans: ["'DM Sans'", "sans-serif"],
        mono: ["'DM Mono'", "monospace"],
      },
      borderRadius: {
        input: "6px",
        button: "8px",
        card: "12px",
        pill: "9999px",
      },
      spacing: {
        4: "4px",
        8: "8px",
        16: "16px",
        24: "24px",
        40: "40px",
        64: "64px",
      },
    },
  },
  plugins: [],
} satisfies Config;
