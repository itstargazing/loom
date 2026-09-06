import path from "node:path";
import { fileURLToPath } from "node:url";

const dashboardDir = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  turbopack: {
    //  Turbopack (the default bundler since Next 16) refuses to resolve paths
    //  that escape its root, which breaks the shared design system imported
    //  from ../shared. Point the root at the monorepo instead of dashboard/.
    root: path.join(dashboardDir, ".."),
  },
};

export default nextConfig;
