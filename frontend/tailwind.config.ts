import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Operational dark surface palette.
        surface: {
          DEFAULT: "#0b0f17",
          raised: "#111725",
          panel: "#161d2d",
          border: "#243149",
        },
        brand: {
          DEFAULT: "#3b82f6",
          fg: "#93c5fd",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
