// tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        seekle: {
          cream: "#faf7f2",
          surface: "#ffffff",
          muted: "#f6f1e8",
          border: "#e4e4e7",
          brown: "#6b4f3c",
          brownHover: "#5b3f2f",
          text: "#18181b",
          subtext: "#52525b",
        },
      },
      boxShadow: {
        soft: "0 1px 2px rgba(16,24,40,0.06), 0 1px 3px rgba(16,24,40,0.10)",
      },
    },
  },
  plugins: [],
};

export default config;
