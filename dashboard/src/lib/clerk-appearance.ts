/** Shared Clerk chrome — monochrome LOOM stage. */
export const clerkAppearance = {
  variables: {
    colorPrimary: "#f2f0ec",
    colorBackground: "#0d0d0d",
    colorInputBackground: "#050505",
    colorNeutral: "#f2f0ec",
    colorText: "#f2f0ec",
    colorTextSecondary: "#9a988f",
    colorDanger: "#d4d0c8",
    borderRadius: "0.85rem",
  },
  elements: {
    card: "bg-[#0d0d0d] shadow-none border border-white/10",
    headerTitle: "text-[#f2f0ec]",
    headerSubtitle: "text-[#9a988f]",
    socialButtonsBlockButton:
      "bg-white/5 border-white/10 text-[#f2f0ec] hover:bg-white/10",
    formFieldLabel: "text-[#9a988f]",
    formFieldInput: "bg-[#050505] border-white/10 text-[#f2f0ec]",
    footerActionLink: "text-[#f2f0ec] hover:text-[#e8e6e0]",
    identityPreviewEditButton: "text-[#f2f0ec]",
  },
} as const;
