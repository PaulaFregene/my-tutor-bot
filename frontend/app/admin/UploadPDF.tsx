"use client";
import { useState } from "react";
import { useAnonUserId, isAdmin } from "../../lib/auth";

export default function UploadPDF() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState("");
  const anonUserId = useAnonUserId();

  if (!anonUserId || !isAdmin(anonUserId)) {
    return <p className="text-red-600">Access denied. Admins only.</p>;
  }

  const handleUpload = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append("pdf", file);

    const res = await fetch("/api/upload_pdf", {
      method: "POST",
      body: formData,
    });

    setStatus(res.ok ? "Upload successful!" : "Upload failed.");
  };

  return (
    <div className="max-w-lg mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Upload Course PDF</h1>
      <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      <button onClick={handleUpload} className="ml-2 px-4 py-2 bg-blue-600 text-white rounded">Upload</button>
      {status && <p className="mt-2">{status}</p>}
    </div>
  );
}
