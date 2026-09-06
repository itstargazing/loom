import path from "node:path";
import { fileURLToPath } from "node:url";

const dashboardDir = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const monorepoRoot = path.join(dashboardDir, "..");

const nextConfig = {
  reactStrictMode: true,
  //  The design system and bridge live in ../shared. Vercel + Next file
  //  tracing must treat the repo root as the project, not dashboard/.
  outputFileTracingRoot: monorepoRoot,
  turbopack: {
    root: monorepoRoot,
  },
};

export default nextConfig;
