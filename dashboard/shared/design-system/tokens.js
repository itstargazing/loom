/**
 * Keep in sync with tokens.ts.
 * Tailwind / Node resolve this .js file first when the extension is omitted.
 */
export const colors = {
  background: "#050505",
  "background-secondary": "#0d0d0d",
  "bg-0": "#050505",
  "bg-1": "#0d0d0d",
  glass: "rgba(255,255,255,0.055)",
  "glass-2": "rgba(255,255,255,0.09)",
  "text-primary": "#F2F0EC",
  "text-secondary": "#9A988F",
  "text-faint": "#5C5A54",
  border: "rgba(255,255,255,0.14)",
  "border-soft": "rgba(255,255,255,0.08)",
  sheen: "rgba(255,255,255,0.18)",
  accent: "#F2F0EC",
  hover: "#E8E6E0",
  success: "#C8C6BE",
  "success-muted": "rgba(255,255,255,0.08)",
  warning: "#9A988F",
  "warning-muted": "rgba(255,255,255,0.06)",
  error: "#D4D0C8",
  "error-muted": "rgba(255,255,255,0.09)",
};

export const fonts = {
  display: ["Space Grotesk", "system-ui", "sans-serif"],
  sans: ["system-ui", "Segoe UI", "sans-serif"],
  mono: ["JetBrains Mono", "ui-monospace", "monospace"],
};

export const fontSizes = {
  xs: ["11px", { lineHeight: "16px" }],
  sm: ["13px", { lineHeight: "20px" }],
  base: ["14px", { lineHeight: "22px" }],
  lg: ["16px", { lineHeight: "24px" }],
  xl: ["20px", { lineHeight: "28px" }],
  "2xl": ["24px", { lineHeight: "32px" }],
  stage: ["96px", { lineHeight: "0.9" }],
};

export const spacing = {
  xs: "4px",
  sm: "8px",
  md: "16px",
  lg: "24px",
  xl: "32px",
  "2xl": "48px",
  "3xl": "64px",
};

export const borderRadius = {
  none: "0",
  sm: "8px",
  DEFAULT: "12px",
  glass: "28px",
  pill: "999px",
};

export const boxShadow = {
  none: "none",
  subtle: "inset 0 1px 0 rgba(255, 255, 255, 0.06)",
  elevation: "inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 20px 50px rgba(0, 0, 0, 0.35)",
  glass: "inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 20px 50px rgba(0, 0, 0, 0.35)",
};

export const transitionDuration = {
  fast: "150ms",
  DEFAULT: "200ms",
  slow: "300ms",
};

export const transitionTiming = {
  DEFAULT: "ease-out",
  in: "ease-in",
};

export const cssVariables = {
  "--bg-0": colors["bg-0"],
  "--bg-1": colors["bg-1"],
  "--glass": colors.glass,
  "--glass-2": colors["glass-2"],
  "--border": colors.border,
  "--border-soft": colors["border-soft"],
  "--text": colors["text-primary"],
  "--text-dim": colors["text-secondary"],
  "--text-faint": colors["text-faint"],
  "--sheen": colors.sheen,
  "--loom-background": colors.background,
  "--loom-background-secondary": colors["background-secondary"],
  "--loom-text-primary": colors["text-primary"],
  "--loom-text-secondary": colors["text-secondary"],
  "--loom-text-faint": colors["text-faint"],
  "--loom-border": colors.border,
  "--loom-border-soft": colors["border-soft"],
  "--loom-accent": colors.accent,
  "--loom-hover": colors.hover,
  "--loom-success": colors.success,
  "--loom-success-muted": colors["success-muted"],
  "--loom-warning": colors.warning,
  "--loom-warning-muted": colors["warning-muted"],
  "--loom-error": colors.error,
  "--loom-error-muted": colors["error-muted"],
  "--loom-font-display": fonts.display.join(", "),
  "--loom-font-sans": fonts.sans.join(", "),
  "--loom-font-mono": fonts.mono.join(", "),
  "--loom-radius-glass": borderRadius.glass,
  "--loom-transition-fast": transitionDuration.fast,
  "--loom-transition": transitionDuration.DEFAULT,
  "--loom-transition-slow": transitionDuration.slow,
};
