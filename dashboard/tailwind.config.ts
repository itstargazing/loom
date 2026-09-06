import type { Config } from "tailwindcss";
import loomPreset from "./shared/design-system/tailwind.preset";

const config: Config = {
  presets: [loomPreset],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./shared/design-system/**/*.{ts,css}",
  ],
  plugins: [],
};

export default config;
