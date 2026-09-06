//  Flat config: Next.js 16 removed `next lint`, and `next build` no longer runs
//  ESLint at all, so linting is invoked directly via `npm run lint`.
import coreWebVitals from "eslint-config-next/core-web-vitals";
import typescript from "eslint-config-next/typescript";

const config = [
  ...coreWebVitals,
  ...typescript,
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts"],
  },
];

export default config;
