import type { Metadata } from "next";

import { Sidebar } from "@/components/sidebar";

import "./globals.css";

export const metadata: Metadata = {
  title: "LOOM Dashboard",
  description: "View captured and compiled output from the LOOM pipeline.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen flex-col md:flex-row">
          <Sidebar />
          <main className="min-w-0 flex-1 px-md py-xl sm:px-xl">
            <div className="mx-auto w-full max-w-[1100px]">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
