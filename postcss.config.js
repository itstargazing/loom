const path = require("node:path");

const dashboard = path.join(__dirname, "dashboard");

module.exports = {
  plugins: {
    [require.resolve("tailwindcss", { paths: [dashboard] })]: {
      config: path.join(dashboard, "tailwind.config.ts"),
    },
    [require.resolve("autoprefixer", { paths: [dashboard] })]: {},
  },
};
