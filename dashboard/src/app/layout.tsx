import { ClerkProvider } from "@clerk/nextjs";
import { Analytics } from "@vercel/analytics/next";
import type { Metadata } from "next";
import type { ReactNode } from "react";

import { isClerkConfigured } from "@/lib/auth-mode";
import { clerkAppearance } from "@/lib/clerk-appearance";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "LOOM",
    template: "%s — LOOM",
  },
  description: "The memory layer for your browser.",
  icons: {
    icon: "/brand/loom-mark-flat.png?v=horn-1",
    apple: "/brand/loom-mark-flat.png?v=horn-1",
  },
};

function Providers({ children }: { children: ReactNode }) {
  if (!isClerkConfigured()) {
    return <>{children}</>;
  }
  return (
    <ClerkProvider
      appearance={clerkAppearance}
      signInFallbackRedirectUrl="/overview"
      signUpFallbackRedirectUrl="/overview"
    >
      {children}
    </ClerkProvider>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <Providers>{children}</Providers>
        <Analytics />
      </body>
    </html>
  );
}
