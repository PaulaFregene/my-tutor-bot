"use client";

export default function ModeSelector({
  mode,
  setMode,
}: {
  mode: string;
  setMode: (m: string) => void;
}) {
  const isSocratic = mode === "socratic";

  return (
    <div className="flex items-center justify-between bg-white p-3 rounded-lg border border-gray-200 shadow-sm mb-4">
      <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Tutor Mode</span>
      <div className="flex items-center gap-3">
        <span className={`text-sm font-medium ${isSocratic ? "text-[#4E2A84]" : "text-gray-400"}`}>
          Socratic Hint
        </span>
        <button
          onClick={() => setMode(isSocratic ? "direct" : "socratic")}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
            isSocratic ? "bg-[#4E2A84]" : "bg-green-500"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              isSocratic ? "translate-x-1" : "translate-x-6"
            }`}
          />
        </button>
        <span className={`text-sm font-medium ${!isSocratic ? "text-green-600" : "text-gray-400"}`}>
          Direct Answer
        </span>
      </div>
    </div>
  );
}
