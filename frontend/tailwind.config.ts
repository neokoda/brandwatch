import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Plus Jakarta Sans", "system-ui", "sans-serif"],
      },
      colors: {
        // Base scale — white/black only
        background: "var(--background)",
        foreground: "var(--foreground)",

        // Structural grays
        border: "var(--border)",
        "border-subtle": "var(--border-subtle)",
        surface: "var(--surface)",
        "surface-raised": "var(--surface-raised)",
        muted: "var(--muted)",
        "muted-foreground": "var(--muted-foreground)",

        // Interactive
        ring: "var(--ring)",

        // Semantic — kept to an absolute minimum, single-hue
        positive: "var(--positive)",
        "positive-subtle": "var(--positive-subtle)",
        negative: "var(--negative)",
        "negative-subtle": "var(--negative-subtle)",
        warning: "var(--warning)",
        "warning-subtle": "var(--warning-subtle)",
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        sm: "calc(var(--radius) - 2px)",
        lg: "calc(var(--radius) + 2px)",
        xl: "calc(var(--radius) + 4px)",
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        card: "0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.06)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "slide-in-left": {
          from: { transform: "translateX(-100%)" },
          to: { transform: "translateX(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.15s ease-out",
        "slide-in-left": "slide-in-left 0.2s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
