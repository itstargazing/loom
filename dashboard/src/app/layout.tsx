import type { Metadata } from "next";

import { AskBar } from "@/components/ask-bar";
import { NotificationBell } from "@/components/notification-bell";
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
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <div className="flex min-h-screen flex-col md:flex-row">
          <Sidebar />
          <main className="min-w-0 flex-1 px-md py-xl sm:px-xl">
            <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-lg">
            <div className="loom-glass loom-glass-nested loom-sheen-tr flex items-center gap-md px-md py-sm">
                <AskBar />
                <NotificationBell />
              </div>
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
