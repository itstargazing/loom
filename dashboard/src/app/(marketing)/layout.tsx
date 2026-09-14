import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";
import type { ReactNode } from "react";

import "@/components/marketing/marketing.css";

const display = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-loom-display",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-loom-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "LOOM — Learning infrastructure for your browser",
  description:
    "LOOM is the memory layer for your browser. Ambient capture, structured documents, contradictions, and answers grounded in what you actually read.",
  openGraph: {
    title: "LOOM — Learning infrastructure for your browser",
    description:
      "Ambient capture → classify → route → ask. Memory for non-linear research.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LOOM — Learning infrastructure for your browser",
    description:
      "The memory layer for your browser. Built for people who don't learn linearly.",
  },
};

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <div className={`${display.variable} ${mono.variable}`}>{children}</div>
  );
}
