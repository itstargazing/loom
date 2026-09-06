import { cpSync, existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const dashboardDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const source = path.join(dashboardDir, "..", "shared");
const dest = path.join(dashboardDir, "shared");

if (!existsSync(source)) {
  if (existsSync(dest)) {
    process.exit(0);
  }
  console.error("Missing shared design system (expected ../shared or ./shared).");
  process.exit(1);
}

mkdirSync(dest, { recursive: true });
cpSync(source, dest, { recursive: true });
