"use client";

import { useState, useEffect } from "react";
import ConsentScreen from "../auth/consent";
import ChatMessage from "./ChatMessage";
import ModeSelector from "./ModeSelector";
import { useAnonUserId, useUsername } from "../../lib/auth";

type ChatMessageType = {
    role: "user" | "assistant";
    content: string;
    citations?: string[];
    [key: string]: unknown;
};

export default function ChatPage() {
    // State for IRB consent
    const [consented, setConsented] = useState(false);

    // Chat State
    const [messages, setMessages] = useState<ChatMessageType[]>([]);
    const [input, setInput] = useState("");
    const [mode, setMode ] = useState("answer");
    const anonUserId = useAnonUserId();
    const username = useUsername();

    // Fetch conversation history when user logs in
    useEffect(() => {
    if (!anonUserId || !consented) return;

    fetch("/api/history", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ anon_user_id: anonUserId }),
    })
      .then((res) => res.json())
      .then((data) => setMessages(data.conversation || []));
  }, [anonUserId, consented]);

    // Handle sending a message
    const handleSubmit = async () => {
        if (!input.trim()) return;
        const newMessage: ChatMessageType = { role: "user", content: input };
        setMessages([...messages, newMessage]);

        // Query backend
        const res = await fetch("/api/query", {
            method: "POST",
            body: JSON.stringify({ question: input, mode, anon_user_id: anonUserId }),
        });
        const data = await res.json();
        setMessages((prev) => [...prev, data]);
        setInput("");
    };

    // If not consented, show IRB consent page
    if (!consented) {
        return <ConsentScreen onConsent={() => setConsented(true)} />;
    }

    // Chat UI once consent is given
  return (
    <div className="max-w-3xl mx-auto p-4">
      <p className="text-gray-600 mb-2">Logged in as: {username}</p>

      <ModeSelector mode={mode} setMode={setMode} />

      <div className="border p-2 h-96 overflow-y-scroll mb-4">
        {messages.map((m, idx) => (
          <ChatMessage key={idx} message={m} />
        ))}
      </div>

      <div className="flex">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 border p-2 rounded"
          placeholder="Ask a question..."
        />
        <button
          onClick={handleSubmit}
          className="ml-2 px-4 py-2 bg-blue-600 text-white rounded"
        >
          Send
        </button>
      </div>
    </div>
  );
}