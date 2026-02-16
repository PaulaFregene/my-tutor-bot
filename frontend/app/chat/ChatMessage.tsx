interface ChatMessageProps {
  message: {
    role: "assistant" | "user";
    content: string;
    citations?: string[];
  };
}

export default function ChatMessage({ message }: ChatMessageProps) {
  return (
    <div className={`mb-2 ${message.role === "assistant" ? "text-left" : "text-right"}`}>
      <div
        className={`inline-block p-2 rounded ${message.role === "assistant" ? "bg-gray-100" : "bg-[#4E2A84]/10"}`}
      >
        <p>{message.content}</p>
        {message.citations && (
          <p className="text-xs text-gray-500 mt-1">{message.citations.join(", ")}</p>
        )}
      </div>
    </div>
  );
}
