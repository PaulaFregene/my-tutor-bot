export default function ModeSelector({ mode, setMode }: { mode: string; setMode: (m: string) => void }) {
  return (
    <div className="mb-2 flex space-x-2">
      {["answer", "tutor", "quiz"].map((m) => (
        <button
          key={m}
          className={`px-3 py-1 rounded ${mode === m ? "bg-blue-600 text-white" : "bg-gray-200"}`}
          onClick={() => setMode(m)}
        >
          {m.charAt(0).toUpperCase() + m.slice(1)}
        </button>
      ))}
    </div>
  );
}
