"use client";

import { useState, useEffect, ReactNode } from "react";
import { RedirectToSignIn, useAuth } from "@clerk/nextjs";
import ConsentScreen from "./consent";

const CONSENT_KEY = "mytutorbot-consent";

export default function ConsentGate({ children }: { children: ReactNode }) {
  const [consented, setConsented] = useState(false);
  const [isChecked, setIsChecked] = useState(false);
  const { isSignedIn, isLoaded: authLoaded } = useAuth();

  useEffect(() => {
    // We use a small timeout to push this check to the next event loop tick.
    // This satisfies React's warning about "synchronous" updates inside effects.
    const timer = setTimeout(() => {
      if (typeof window !== "undefined") {
        const stored = window.sessionStorage.getItem(CONSENT_KEY);
        if (stored === "true") {
          setConsented(true);
        }
      }
      setIsChecked(true);
    }, 0);

    return () => clearTimeout(timer);
  }, []);

  const handleConsent = () => {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(CONSENT_KEY, "true");
    }
    setConsented(true);
  };

  // 1. Wait for Auth to load AND our Storage check to finish
  // displaying nothing (or a loader) prevents flickering
  if (!authLoaded || !isChecked) {
    return null;
  }

  // 2. If user hasn't consented yet, show the Consent Screen
  if (!consented) {
    // Note: We use 'return' here to block the children from rendering
    return <ConsentScreen onConsent={handleConsent} />;
  }

  // 3. If consented but not signed in, force Clerk sign-in
  if (!isSignedIn) {
    return <RedirectToSignIn />;
  }

  // 4. Happy Path: User consented AND is signed in -> Show the App
  return <>{children}</>;
}
