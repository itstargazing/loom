import type { Config } from "tailwindcss";
import loomPreset from "../shared/design-system/tailwind.preset";

const config: Config = {
  presets: [loomPreset],
  content: ["./src/**/*.{html,ts,tsx}", "../shared/design-system/**/*.{ts,css}"],
  plugins: [],
};

export default config;
