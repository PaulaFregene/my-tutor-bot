import { ClerkProvider } from "@clerk/nextjs";
import { ReactNode } from "react";
import type { Metadata } from "next";
import "./globals.css";
import ConsentGate from "./auth/ConsentGate";

export const metadata: Metadata = {
  title: "My Tutor Bot",
  icons: {
    icon: "/tutorbot-logo.png",
  },
};

// Wraps entire frontend app with Clerk Auth
// Only signedon users see chat/admin pages

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      {/* suppressHydrationWarning prevents errors caused by browser extensions like Grammarly */}
      <body suppressHydrationWarning={true}>
        <ClerkProvider>
          <ConsentGate>{children}</ConsentGate>
        </ClerkProvider>
      </body>
    </html>
  );
}
