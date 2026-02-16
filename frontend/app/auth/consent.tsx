"use client";
import { useState } from "react";
import Image from "next/image";

interface ConsentProps {
  onConsent: () => void;
}

export default function ConsentScreen({ onConsent }: ConsentProps) {
  const [checked, setChecked] = useState(false);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-4 fixed inset-0 z-50">
      <div className="bg-white p-8 rounded-2xl shadow-xl max-w-md w-full text-center border border-gray-100">
        <div className="mx-auto mb-6 relative w-24 h-24 rounded-full overflow-hidden border-4 border-[#4E2A84] shadow-md bg-white">
          <Image
            src="/icon.png"
            alt="My Tutor Bot logo"
            fill
            className="object-cover object-center"
          />
        </div>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">Consent for Research</h1>

        <div className="text-sm text-gray-600 mb-6 leading-relaxed text-left">
          <p className="mb-2">
            Your interactions with this AI assistant will be logged for research purposes.
          </p>
          <p>No personal information will be stored beyond your anonymous user ID.</p>
        </div>

        <div
          onClick={() => setChecked(!checked)}
          className="flex items-center justify-center gap-3 mb-6 bg-gray-50 p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-100 transition-colors"
        >
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
            className="w-5 h-5 text-[#4E2A84] rounded focus:ring-[#4E2A84] cursor-pointer"
          />
          <label className="text-sm font-medium text-gray-700 cursor-pointer select-none">
            I consent to participate in this research.
          </label>
        </div>

        <button
          onClick={onConsent}
          disabled={!checked}
          className={`w-full py-3 px-4 rounded-xl font-semibold transition-all duration-200 ${
            checked
              ? "bg-[#4E2A84] text-white shadow-lg hover:bg-[#3d1f63] transform hover:-translate-y-0.5"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
