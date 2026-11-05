/**
 * Design tokens for the examination console.
 *
 * The palette is deliberately restrained and semantic rather than decorative: one neutral
 * scale, and colour reserved for verdicts. Amber means a critical finding, teal means
 * compliant, slate means unestablishable. A reviewer learning "amber = you should not pay"
 * once can read every screen afterwards, which matters more here than looking novel.
 */
import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0b0e13",
          900: "#11151c",
          850: "#161b23",
          800: "#1c222c",
          700: "#2a323f",
          600: "#3d4757",
          400: "#7c8899",
          300: "#9fabbb",
          100: "#dfe4ea",
        },
        verdict: {
          critical: "#e0a34a",
          compliant: "#4ec9a8",
          minor: "#7aa2d6",
          unresolved: "#a99ad6",
          error: "#d97373",
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Segoe UI", "Helvetica Neue", "sans-serif"],
        mono: ["ui-monospace", "Cascadia Mono", "Consolas", "monospace"],
      },
      fontVariantNumeric: { tabular: "tabular-nums" },
      maxWidth: { console: "1500px" },
    },
  },
  plugins: [],
} satisfies Config;
