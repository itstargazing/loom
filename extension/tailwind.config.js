import loomPreset from "../shared/design-system/tailwind.preset";
const config = {
    presets: [loomPreset],
    content: ["./src/**/*.{html,ts,tsx}", "../shared/design-system/**/*.{ts,css}"],
    plugins: [],
};
export default config;
