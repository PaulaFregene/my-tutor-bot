import { ClerkProvider, SignedIn, SignedOut, RedirectToSignIn } from "@clerk/nextjs"; 
import { ReactNode } from "react";


// Wraps entire frontend app with Clerk Auth
// Only signedon users see chat/admin pages

export default function RootLayout({ children }: {children: ReactNode}) {
  return (
    <html>
      <body>
        <ClerkProvider>
          <SignedIn>{children}</SignedIn>
          <SignedOut>
            <RedirectToSignIn />
          </SignedOut>
        </ClerkProvider>
      </body>
    </html>
  );
}