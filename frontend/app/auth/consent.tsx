"use client";
import { useState } from "react";

interface ConsentProps {
  onConsent: () => void;
}

export default function ConsentScreen({ onConsent }: ConsentProps) {
  const [checked, setChecked] = useState(false);

  return (
    <div className="p-4 max-w-lg mx-auto text-center">
      <h1 className="text-2xl font-bold mb-4">Consent for Research</h1>
      <p className="mb-4">
        Your interactions with this AI assistant will be logged for research purposes.
        No personal information will be stored beyond your anonymous user ID.
      </p>
      <label className="flex items-center mb-4 justify-center">
        <input
          type="checkbox"
          checked={checked}
          onChange={() => setChecked(!checked)}
          className="mr-2"
        />
        I consent to participate in this research.
      </label>
      <div>
        <button
          disabled={!checked}
          onClick={onConsent}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
