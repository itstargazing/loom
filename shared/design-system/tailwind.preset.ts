import {
  borderRadius,
  boxShadow,
  fontSizes,
  fonts,
  spacing,
  transitionDuration,
  transitionTiming,
} from "./tokens";

//  Deliberately not typed as Tailwind's `Config`. This directory is shared by
//  the dashboard and the extension and has no node_modules of its own, so a
//  `tailwindcss` import fails to resolve when a consumer type-checks this file.
//  Each consumer's tailwind.config.ts is typed as `Config`, which is where this
//  object gets checked against Tailwind's expected preset shape.
const preset = {
  theme: {
    extend: {
      colors: {
        //  CSS variables so a stale compiled tokens.js cannot paint the old
        //  light palette over the dark glass theme.
        background: "var(--loom-background)",
        "background-secondary": "var(--loom-background-secondary)",
        "bg-0": "var(--bg-0)",
        "bg-1": "var(--bg-1)",
        glass: "var(--glass)",
        "glass-2": "var(--glass-2)",
        "text-primary": "var(--loom-text-primary)",
        "text-secondary": "var(--loom-text-secondary)",
        "text-faint": "var(--loom-text-faint)",
        border: "var(--loom-border)",
        "border-soft": "var(--loom-border-soft)",
        sheen: "var(--sheen)",
        accent: "var(--loom-accent)",
        hover: "var(--loom-hover)",
        success: "var(--loom-success)",
        "success-muted": "var(--loom-success-muted)",
        warning: "var(--loom-warning)",
        "warning-muted": "var(--loom-warning-muted)",
        error: "var(--loom-error)",
        "error-muted": "var(--loom-error-muted)",
      },
      fontFamily: {
        display: fonts.display,
        sans: fonts.sans,
        mono: fonts.mono,
      },
      fontSize: fontSizes,
      spacing,
      borderRadius,
      boxShadow,
      transitionDuration,
      transitionTimingFunction: transitionTiming,
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "fade-out": {
          from: { opacity: "1" },
          to: { opacity: "0" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "slide-down": {
          from: { opacity: "0", transform: "translateY(-8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "thread-draw": {
          "0%": { strokeDashoffset: "1", opacity: "0" },
          "12%": { opacity: "1" },
          "42%": { strokeDashoffset: "0", opacity: "1" },
          "62%": { strokeDashoffset: "0", opacity: "0.75" },
          "78%": { strokeDashoffset: "0", opacity: "0" },
          "100%": { strokeDashoffset: "1", opacity: "0" },
        },
      },
      animation: {
        "fade-in": "fade-in 200ms ease-out forwards",
        "fade-out": "fade-out 200ms ease-in forwards",
        "slide-up": "slide-up 250ms ease-out forwards",
        "slide-down": "slide-down 250ms ease-out forwards",
        "thread-draw": "thread-draw 4.8s ease-in-out infinite",
      },
    },
  },
};

export default preset;
