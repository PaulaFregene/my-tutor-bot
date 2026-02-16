"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Image from "next/image";
import { useClerk } from "@clerk/nextjs";
import ModeSelector from "./ModeSelector";
import { useAnonUserId, useUsername, useIsAdmin } from "../../lib/auth";

// --- CONFIGURATION ---
// This automatically picks the right URL based on where the code is running
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
// ---------------------

type Message = {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("socratic");

  // State for the PDF Viewer
  const [files, setFiles] = useState<string[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [displayNames, setDisplayNames] = useState<Record<string, string>>({}); // Filename -> Display Name
  const [editingFile, setEditingFile] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");

  // Loading state for AI processing
  const [isLoading, setIsLoading] = useState(false);
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [showAboutModal, setShowAboutModal] = useState(false);
  const [showSurveyModal, setShowSurveyModal] = useState(false);
  const [surveyPrompted, setSurveyPrompted] = useState(false);
  const [surveyReminderScheduled, setSurveyReminderScheduled] = useState(false);
  const [surveyAttention, setSurveyAttention] = useState(false);
  const [surveyFromSignOut, setSurveyFromSignOut] = useState(false);
  const surveyUrl = "https://www.google.com";
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Sidebar toggle state
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Chat column width state (in pixels)
  const [chatWidth, setChatWidth] = useState(384); // w-96 = 24rem = 384px
  const [isDragging, setIsDragging] = useState(false);

  // References
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Handle draggable edge for chat column
  const handleMouseDown = () => {
    setIsDragging(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;

      // Get the right edge position and calculate new width
      const newWidth = window.innerWidth - e.clientX;
      // Constrain width between 280px and 600px
      if (newWidth >= 280 && newWidth <= 600) {
        setChatWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "default";
      document.body.style.userSelect = "auto";
    };
  }, [isDragging]);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (surveyPrompted) return;

    const timer = setTimeout(
      () => {
        setShowSurveyModal(true);
        setSurveyPrompted(true);
        setSurveyAttention(true);
      },
      10 * 60 * 1000
    );

    return () => clearTimeout(timer);
  }, [surveyPrompted]);

  const scheduleSurveyReminder = () => {
    if (surveyReminderScheduled) return;
    setSurveyReminderScheduled(true);
    setTimeout(
      () => {
        setShowSurveyModal(true);
        setSurveyFromSignOut(false);
        setSurveyReminderScheduled(false);
        setSurveyAttention(true);
      },
      10 * 60 * 1000
    );
  };

  const anonUserId = useAnonUserId();
  const username = useUsername();
  const userIsAdmin = useIsAdmin();
  const { signOut } = useClerk();

  // Refresh file list with retry logic
  const refreshFiles = useCallback(
    async (maxRetries = 3) => {
      for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
          // UPDATED: Using API_BASE_URL
          const res = await fetch(`${API_BASE_URL}/api/files`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);

          const data = await res.json();
          setFiles(data.files || []);
          setDisplayNames(data.display_names || {});
          if (data.files && data.files.length > 0 && !activeFile) {
            setActiveFile(data.files[0]);
          }
          return; // Success - exit retry loop
        } catch (e) {
          console.error(`Error fetching files (attempt ${attempt + 1}/${maxRetries}):`, e);

          if (attempt < maxRetries - 1) {
            // Wait before retrying (exponential backoff)
            await new Promise((resolve) => setTimeout(resolve, 2 ** attempt * 1000));
          } else {
            // All retries exhausted
            console.warn("Failed to fetch files after", maxRetries, "attempts");
            setFiles([]); // Clear file list on failure
          }
        }
      }
    },
    [activeFile]
  );

  // Handle file delete
  const handleDeleteFile = async (filename: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering file selection

    if (
      !confirm(
        `Are you sure you want to delete "${filename}"? This will also remove it from the database.`
      )
    ) {
      return;
    }

    try {
      // UPDATED: Using API_BASE_URL
      const res = await fetch(`${API_BASE_URL}/api/delete-pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename }),
      });

      const data = await res.json();
      if (res.ok) {
        console.log(`Deleted ${filename}`);
        // Clear file selection if deleted file was active
        if (activeFile === filename) {
          setActiveFile(null);
        }
        // Refresh file list
        await refreshFiles();
      } else {
        alert(`Failed to delete: ${data.message}`);
      }
    } catch (e) {
      console.error("Delete error:", e);
      alert("Error deleting file");
    }
  };

  // Handle edit button click - enter edit mode
  const handleEditClick = (filename: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingFile(filename);
    setEditingName(displayNames[filename] || filename);
  };

  // Handle save display name
  const handleSaveDisplayName = async (filename: string) => {
    try {
      // UPDATED: Using API_BASE_URL
      const res = await fetch(`${API_BASE_URL}/api/set-display-name`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, display_name: editingName }),
      });

      if (res.ok) {
        await res.json();
        setDisplayNames((prev) => ({ ...prev, [filename]: editingName }));
        setEditingFile(null);
        setEditingName("");
      } else {
        alert("Failed to save display name");
      }
    } catch (e) {
      console.error("Save error:", e);
      alert("Error saving display name");
    }
  };

  // Handle cancel editing
  const handleCancelEdit = () => {
    setEditingFile(null);
    setEditingName("");
  };

  // Handle file upload with retry logic
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith(".pdf")) {
      setUploadStatus("Only PDF files are allowed");
      setTimeout(() => setUploadStatus(""), 3000);
      return;
    }

    setUploading(true);
    setUploadStatus("Uploading...");

    const maxRetries = 3;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        // Step 1: Upload the file
        const formData = new FormData();
        formData.append("file", file);

        // UPDATED: Using API_BASE_URL
        const uploadRes = await fetch(`${API_BASE_URL}/api/upload`, {
          method: "POST",
          body: formData,
        });

        if (!uploadRes.ok) {
          throw new Error("Upload failed");
        }

        setUploadStatus("Indexing...");

        // Step 2: Ingest the PDFs
        // UPDATED: Using API_BASE_URL
        const ingestRes = await fetch(`${API_BASE_URL}/api/ingest`, {
          method: "POST",
        });

        if (!ingestRes.ok) {
          throw new Error("Ingestion failed");
        }

        setUploadStatus("✓ Success!");

        // Step 3: Refresh file list
        await refreshFiles();

        // Clear status after 2 seconds
        setTimeout(() => setUploadStatus(""), 2000);
        break; // Success - exit retry loop
      } catch (error) {
        console.error(`Upload attempt ${attempt + 1}/${maxRetries} failed:`, error);

        if (attempt < maxRetries - 1) {
          // Not the last attempt - retry with backoff
          const delay = 2 ** attempt * 1000; // 1s, 2s, 4s
          setUploadStatus(`Retrying... (${attempt + 2}/${maxRetries})`);
          await new Promise((resolve) => setTimeout(resolve, delay));
        } else {
          // Last attempt failed
          setUploadStatus("✗ Upload failed after 3 attempts");
          setTimeout(() => setUploadStatus(""), 3000);
        }
      }
    }

    setUploading(false);
    // Reset file input
    e.target.value = "";
  };

  // Load History & File List
  useEffect(() => {
    if (!anonUserId) return;

    // Fetch History with error handling
    // UPDATED: Using API_BASE_URL
    fetch(`${API_BASE_URL}/api/history`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ anon_user_id: anonUserId }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setMessages(data.conversation || []))
      .catch((e) => {
        console.error("Error fetching history:", e);
        // Don't show error to user, just log it
      });

    // Fetch Files with retries
    refreshFiles(3);
  }, [anonUserId, refreshFiles]);

  // Auto-scroll to bottom of chat when messages change or AI is loading
  useEffect(() => {
    if (chatContainerRef.current) {
      setTimeout(() => {
        chatContainerRef.current?.scrollTo({
          top: chatContainerRef.current.scrollHeight,
          behavior: "smooth",
        });
      }, 0);
    }
  }, [messages, isLoading]);

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return;
    const userMsg: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    const question = input;
    setInput("");
    setIsLoading(true);

    try {
      // UPDATED: Using API_BASE_URL
      const res = await fetch(`${API_BASE_URL}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question,
          mode,
          anon_user_id: anonUserId,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMessages((prev) => [...prev, data]);
    } catch (e) {
      console.error("Query error:", e);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, I'm unable to reach the server. Please check that the backend is running.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-gray-100 font-sans">
      {/* HEADER */}
      <header className="bg-gradient-to-r from-[#4E2A84] via-[#5b3796] to-[#3d1f63] text-white px-5 py-3 flex justify-between items-center shadow-lg h-16 shrink-0 relative">
        <div className="flex items-center gap-3">
          <div className="relative w-10 h-10 rounded-full overflow-hidden ring-2 ring-white/60 shrink-0 bg-[#3d1f63]">
            <Image
              src="/tutorbot-logo.png"
              alt="My Tutor Bot logo"
              fill
              className="object-cover object-center"
            />
          </div>
          <div className="leading-tight">
            <h1 className="text-xl font-bold tracking-tight">My Tutor Bot</h1>
            <p className="text-[11px] text-white/70 hidden md:block">
              AI-Powered Interactive Tutor - CS 211 Research Created By Paula Eyituoyo Fregene
            </p>
          </div>
        </div>
        <div className="absolute left-1/2 -translate-x-1/2 hidden md:block">
          <button
            onClick={() => {
              setShowSurveyModal(true);
              setSurveyAttention(false);
              setSurveyFromSignOut(false);
            }}
            className="text-sm font-semibold px-5 py-2 rounded-full bg-white/20 hover:bg-white/30 transition-colors border border-white/40 relative shadow-sm"
          >
            Take Survey
            {surveyAttention && (
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-rose-400 ring-2 ring-[#4E2A84]" />
            )}
          </button>
        </div>
        <div className="hidden md:flex items-center gap-2">
          <button
            onClick={() => setShowConsentModal(true)}
            className="text-xs font-semibold px-3 py-1 rounded-full bg-white/10 hover:bg-white/20 transition-colors border border-white/20"
          >
            Consent
          </button>
          <button
            onClick={() => setShowHelpModal(true)}
            className="text-xs font-semibold px-3 py-1 rounded-full bg-white/10 hover:bg-white/20 transition-colors border border-white/20"
          >
            Help
          </button>
          <button
            onClick={() => setShowAboutModal(true)}
            className="text-xs font-semibold px-3 py-1 rounded-full bg-white/10 hover:bg-white/20 transition-colors border border-white/20"
          >
            About
          </button>
          <div className="text-xs font-semibold bg-white/15 px-3 py-1 rounded-full border border-white/25">
            {username || "Student"}
          </div>
          <button
            onClick={() => {
              setShowSurveyModal(true);
              setSurveyAttention(false);
              setSurveyFromSignOut(true);
            }}
            className="text-xs font-semibold px-3 py-1 rounded-full bg-white/10 hover:bg-white/20 transition-colors flex items-center gap-1 border border-white/20"
          >
            <svg
              viewBox="0 0 24 24"
              className="w-3.5 h-3.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <path d="M16 17l5-5-5-5" />
              <path d="M21 12H9" />
            </svg>
            Sign out
          </button>
        </div>

        <div className="md:hidden flex items-center gap-2">
          <button
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            className="text-xs font-semibold px-3 py-1 rounded-full bg-white/10 hover:bg-white/20 transition-colors border border-white/20"
            aria-expanded={mobileMenuOpen}
            aria-label="Open menu"
          >
            Menu
          </button>
        </div>

        {mobileMenuOpen && (
          <div className="absolute right-4 top-16 z-50 w-48 rounded-lg bg-white text-gray-800 shadow-lg border border-gray-200 md:hidden">
            <button
              onClick={() => {
                setShowSurveyModal(true);
                setSurveyAttention(false);
                setSurveyFromSignOut(false);
                setMobileMenuOpen(false);
              }}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50"
            >
              Take Survey
            </button>
            <button
              onClick={() => {
                setShowConsentModal(true);
                setMobileMenuOpen(false);
              }}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50"
            >
              Consent
            </button>
            <button
              onClick={() => {
                setShowHelpModal(true);
                setMobileMenuOpen(false);
              }}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50"
            >
              Help
            </button>
            <button
              onClick={() => {
                setShowAboutModal(true);
                setMobileMenuOpen(false);
              }}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50"
            >
              About
            </button>
            <div className="px-4 py-2 text-xs text-gray-500 border-t border-gray-200">
              {username || "Student"}
            </div>
            <button
              onClick={() => {
                setShowSurveyModal(true);
                setSurveyAttention(false);
                setSurveyFromSignOut(true);
                setMobileMenuOpen(false);
              }}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50"
            >
              Sign out
            </button>
          </div>
        )}
      </header>

      {/* MAIN LAYOUT */}
      <div className="flex flex-1 overflow-hidden">
        {/* COL 1: SIDEBAR */}
        {sidebarOpen && (
          <aside className="hidden md:flex w-64 bg-white border-r border-gray-200 flex-col p-4 transition-all">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-700 text-sm uppercase">
                CS 211 Course Content
              </h2>
              <button
                onClick={() => setSidebarOpen(false)}
                className="text-gray-500 hover:text-gray-700 transition-colors text-lg"
                title="Hide sidebar"
              >
                ×
              </button>
            </div>

            {/* Upload Button - Admin Only */}
            {userIsAdmin && (
              <div className="mb-4">
                <label className="w-full cursor-pointer">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleFileUpload}
                    disabled={uploading}
                    className="hidden"
                  />
                  <div
                    className={`w-full text-center px-3 py-2 rounded text-sm font-medium transition-colors ${
                      uploading
                        ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                        : "bg-[#4E2A84] text-white hover:bg-[#3d1f63]"
                    }`}
                  >
                    {uploading ? "Uploading..." : "+ Upload PDF"}
                  </div>
                </label>
                {uploadStatus && (
                  <p
                    className={`text-xs mt-2 text-center ${
                      uploadStatus.includes("✓")
                        ? "text-green-600"
                        : uploadStatus.includes("✗")
                          ? "text-red-600"
                          : "text-gray-500"
                    }`}
                  >
                    {uploadStatus}
                  </p>
                )}
              </div>
            )}

            <div className="space-y-1">
              {files.map((file) => (
                <div key={file}>
                  {editingFile === file ? (
                    // Edit mode: Show text input
                    <div className="flex items-center gap-2 px-2 py-1">
                      <input
                        type="text"
                        value={editingName}
                        onChange={(e) => setEditingName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveDisplayName(file);
                          if (e.key === "Escape") handleCancelEdit();
                        }}
                        autoFocus
                        className="flex-1 px-2 py-1 text-sm border border-[#4E2A84] rounded focus:outline-none focus:ring-2 focus:ring-[#4E2A84]"
                      />
                      <button
                        onClick={() => handleSaveDisplayName(file)}
                        className="px-2 py-1 text-green-600 hover:bg-green-50 rounded text-sm font-bold transition-colors"
                        title="Save"
                      >
                        ✓
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="px-2 py-1 text-gray-500 hover:bg-gray-100 rounded text-sm font-bold transition-colors"
                        title="Cancel"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    // Normal mode: Show file with edit/delete buttons
                    <div
                      className={`flex items-center gap-2 rounded transition-colors group ${
                        activeFile === file ? "bg-[#4E2A84]/10" : "hover:bg-gray-50"
                      }`}
                    >
                      <button
                        onClick={() => setActiveFile(file)}
                        className={`flex-1 text-left px-3 py-2 rounded text-sm truncate transition-colors ${
                          activeFile === file ? "text-[#4E2A84] font-medium" : "text-gray-600"
                        }`}
                        title={file}
                      >
                        {displayNames[file] || file}
                      </button>
                      {userIsAdmin && (
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity mr-1">
                          <button
                            onClick={(e) => handleEditClick(file, e)}
                            className="px-2 py-1 text-blue-600 hover:bg-blue-50 rounded text-xs transition-colors"
                            title="Edit display name"
                          >
                            ✏️
                          </button>
                          <button
                            onClick={(e) => handleDeleteFile(file, e)}
                            className="px-2 py-1 text-red-600 hover:bg-red-50 rounded text-xs transition-colors"
                            title="Delete file"
                          >
                            🗑️
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              {files.length === 0 && <p className="text-xs text-gray-400">No PDFs uploaded yet.</p>}
            </div>
          </aside>
        )}

        {/* COL 2: PDF VIEWER */}
        <main className="hidden md:flex flex-1 bg-gray-50 flex flex-col relative border-r border-gray-200">
          <div className="h-12 bg-white border-b border-gray-200 flex items-center px-4 justify-between">
            <div className="flex items-center gap-2">
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="text-gray-600 hover:text-gray-800 transition-colors text-lg"
                  title="Show sidebar"
                >
                  ☰
                </button>
              )}
              <span className="text-sm font-semibold text-gray-700">
                {activeFile ? activeFile : "Select a file"}
              </span>
            </div>
          </div>
          <div className="flex-1 p-4 h-full">
            {activeFile ? (
              <iframe
                // UPDATED: Using API_BASE_URL
                src={`${API_BASE_URL}/pdfs/${activeFile}`}
                className="w-full h-full rounded border border-gray-300 bg-white"
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <div className="relative w-24 h-24 rounded-full overflow-hidden opacity-20 mb-4 bg-gray-200">
                  <Image
                    src="/tutorbot-logo.png"
                    alt="My Tutor Bot"
                    fill
                    className="object-cover object-center"
                  />
                </div>
                <div className="mt-4">Select a lecture to view</div>
              </div>
            )}
          </div>
        </main>

        {/* COL 3: CHAT */}
        {/* Draggable Divider */}
        <div
          onMouseDown={handleMouseDown}
          className={`hidden md:block w-1 bg-gray-300 hover:bg-[#4E2A84] transition-colors cursor-col-resize ${isDragging ? "bg-[#4E2A84]" : ""}`}
          title="Drag to resize chat"
        />

        <aside
          style={{ width: isMobile ? "100%" : `${chatWidth}px` }}
          className="bg-white flex flex-col shadow-xl z-20"
        >
          <div className="p-4 border-b border-gray-200 bg-gray-50">
            <ModeSelector mode={mode} setMode={setMode} />
          </div>

          <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-white">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${m.role === "assistant" ? "bg-white border border-[#4E2A84]/30" : "bg-gray-200"}`}
                >
                  {m.role === "assistant" ? (
                    <div className="relative w-7 h-7 rounded-full overflow-hidden shrink-0">
                      <Image
                        src="/tutorbot-logo.png"
                        alt="My Tutor Bot"
                        fill
                        className="object-cover object-center"
                      />
                    </div>
                  ) : (
                    <span>Me</span>
                  )}
                </div>
                <div
                  className={`p-3 rounded-lg text-sm max-w-[85%] ${m.role === "assistant" ? "bg-[#4E2A84]/5 text-gray-800" : "bg-gray-100"}`}
                >
                  <p>{m.content}</p>
                  {/* Render Citations */}
                  {m.citations && m.citations.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-[#4E2A84]/20">
                      {m.citations.map((cite, i) => (
                        <span key={i} className="block text-xs text-[#4E2A84] truncate">
                          📍 {cite}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {messages.length === 0 && !isLoading && (
              <div className="flex flex-col items-center justify-center text-gray-400 py-12">
                <div className="relative w-16 h-16 rounded-full overflow-hidden opacity-30 bg-gray-200">
                  <Image
                    src="/tutorbot-logo.png"
                    alt="My Tutor Bot"
                    fill
                    className="object-cover object-center"
                  />
                </div>
                <div className="mt-4 text-sm">Ask a question to start the chat.</div>
                <div className="mt-1 text-xs text-gray-400">
                  Loading chat might take a short while.
                </div>
              </div>
            )}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-white border border-[#4E2A84]/30">
                  <div className="relative w-24 h-24 rounded-full overflow-hidden opacity-20 mb-4 bg-gray-200">
                    <Image
                      src="/tutorbot-logo.png"
                      alt="My Tutor Bot"
                      fill
                      className="object-cover object-center"
                    />
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-[#4E2A84]/5 flex items-center gap-2">
                  <span className="text-sm text-gray-600">Thinking</span>
                  <div className="flex gap-1">
                    <span
                      className="w-2 h-2 bg-[#4E2A84] rounded-full animate-bounce"
                      style={{ animationDelay: "0s" }}
                    ></span>
                    <span
                      className="w-2 h-2 bg-[#4E2A84] rounded-full animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    ></span>
                    <span
                      className="w-2 h-2 bg-[#4E2A84] rounded-full animate-bounce"
                      style={{ animationDelay: "0.4s" }}
                    ></span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="p-4 border-t border-gray-100">
            <div className="relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !isLoading && handleSubmit()}
                disabled={isLoading}
                className="w-full border border-gray-300 rounded-xl py-3 px-4 pr-10 focus:ring-2 focus:ring-[#4E2A84] text-sm disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed"
                placeholder="Ask a question..."
              />
              <button
                onClick={handleSubmit}
                disabled={isLoading}
                className={`absolute right-2 top-2.5 ${isLoading ? "text-gray-300 cursor-not-allowed" : "text-[#4E2A84] hover:text-[#3d1f63]"}`}
              >
                {isLoading ? "⏳" : "➤"}
              </button>
            </div>
          </div>
        </aside>
      </div>

      {showConsentModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg relative">
            <button
              onClick={() => setShowConsentModal(false)}
              className="absolute top-3 right-3 text-gray-500 hover:text-gray-700"
              aria-label="Close"
            >
              ×
            </button>
            <div className="p-6">
              <h2 className="text-lg font-semibold mb-3">Research Consent</h2>
              <p className="text-sm text-gray-700 mb-3">
                You have already provided consent to participate in this research study. Your
                interactions with My Tutor Bot are being logged for analysis.
              </p>
              <p className="text-sm text-gray-700 mb-4">
                <strong>Data collected:</strong> Chat messages, file interactions, and user mode
                selections (anonymous).
              </p>
              <p className="text-sm text-gray-700">
                If you do not wish to continue, you can sign out at any time. For questions about
                this study, please contact the research team.
              </p>
            </div>
          </div>
        </div>
      )}

      {showHelpModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg relative">
            <button
              onClick={() => setShowHelpModal(false)}
              className="absolute top-3 right-3 text-gray-500 hover:text-gray-700"
              aria-label="Close"
            >
              ×
            </button>
            <div className="p-6">
              <h2 className="text-lg font-semibold mb-3">How to use My Tutor Bot</h2>
              <p className="text-sm text-gray-700 mb-3">
                Ask questions in the chat and the AI will answer based on the uploaded course PDFs.
              </p>
              <ul className="text-sm text-gray-700 space-y-2 list-disc pl-5">
                <li>Pick a PDF in the left sidebar to view it.</li>
                <li>Use the chat to ask about concepts or examples.</li>
                <li>Check citations in responses to jump to sources.</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {showAboutModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg relative">
            <button
              onClick={() => setShowAboutModal(false)}
              className="absolute top-3 right-3 text-gray-500 hover:text-gray-700"
              aria-label="Close"
            >
              ×
            </button>
            <div className="p-6">
              <h2 className="text-lg font-semibold mb-3">About this research</h2>
              <p className="text-sm text-gray-700 mb-3">
                This tool supports research on AI-assisted learning. Your interactions may be logged
                for analysis, and no personal information is stored beyond your anonymous user ID.
              </p>
              <p className="text-sm text-gray-700">
                If you have questions about the study or data usage, contact the research team.
              </p>
            </div>
          </div>
        </div>
      )}

      {showSurveyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg relative">
            <button
              onClick={() => {
                setShowSurveyModal(false);
                setSurveyAttention(false);
                setSurveyFromSignOut(false);
              }}
              className="absolute top-3 right-3 text-gray-500 hover:text-gray-700"
              aria-label="Close"
            >
              ×
            </button>
            <div className="p-6">
              <h2 className="text-lg font-semibold mb-3">Quick survey</h2>
              <p className="text-sm text-gray-700 mb-4">
                Before you go, would you be willing to take a short survey about your experience?
              </p>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => {
                    setSurveyAttention(false);
                    setShowSurveyModal(false);
                    if (surveyFromSignOut) {
                      signOut();
                      return;
                    }
                    window.open(surveyUrl, "_blank", "noopener,noreferrer");
                  }}
                  className="px-4 py-2 rounded-md bg-[#4E2A84] text-white text-sm font-semibold hover:bg-[#3d1f63] transition-colors"
                >
                  Take survey
                </button>
                <button
                  onClick={() => {
                    setShowSurveyModal(false);
                    setSurveyAttention(false);
                    if (surveyFromSignOut) {
                      signOut();
                      return;
                    }
                    scheduleSurveyReminder();
                  }}
                  className="px-4 py-2 rounded-md bg-gray-100 text-gray-700 text-sm font-semibold hover:bg-gray-200 transition-colors"
                >
                  Remind me later
                </button>
                <button
                  onClick={() => {
                    setShowSurveyModal(false);
                    setSurveyAttention(false);
                    if (surveyFromSignOut) {
                      signOut();
                    }
                  }}
                  className="px-4 py-2 rounded-md bg-white text-gray-700 text-sm font-semibold border border-gray-200 hover:bg-gray-50 transition-colors"
                >
                  Not now
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
