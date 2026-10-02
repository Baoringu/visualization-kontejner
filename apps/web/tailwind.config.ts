import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}", "./messages/**/*.json"],
  theme: {
    extend: {
      borderRadius: { md: "0.5rem", lg: "0.5rem" },
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        muted: "var(--muted)",
      },
    },
  },
  plugins: [],
} satisfies Config;
