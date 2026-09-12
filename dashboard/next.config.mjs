import path from "node:path";
import { fileURLToPath } from "node:url";

const dashboardDir = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Keep Turbopack rooted on the dashboard so PostCSS/Tailwind resolve here,
  // not at the monorepo root (shared/ is copied into dashboard/shared).
  turbopack: {
    root: dashboardDir,
  },
};

export default nextConfig;
