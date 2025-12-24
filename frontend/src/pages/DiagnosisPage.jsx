import React, { useState } from "react";
import UploadImage from "../components/ImageUpload";

export default function DiagnosisPage() {
  const [pageMessage, setPageMessage] = useState("");
  const [lastImageUrl, setLastImageUrl] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState(null);

  async function handleUploadComplete(imageUrl) {
    setLastImageUrl(imageUrl);
    setPageMessage("Upload complete. Running AI...");
    setAiResult(null);
    setAiLoading(true);

    try {
      const res = await fetch("/api/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ imageUrl }) });

      const data = await res.json();
      if (!res.ok) { setPageMessage(data.error || "AI request failed"); setAiLoading(false); return; }

      setAiResult(data);
      setPageMessage("AI result ready.");
      setAiLoading(false);
    } catch (e) {
      setPageMessage("AI request crashed: " + e.message);
      setAiLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 700, padding: "48px 24px" }}>
        <h1 style={{ fontSize: 36, marginBottom: 8 }}>Diagnosis</h1>
        <p style={{ fontSize: 18, color: "#555", marginBottom: 24 }}>Upload a chest X-ray image to begin analysis.</p>

        <div style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 24, background: "#fff" }}>
          <UploadImage userId="test-user" onUploadComplete={handleUploadComplete} />

          {pageMessage && <p style={{ marginTop: 16, fontWeight: 600 }}>{pageMessage}</p>}

          {lastImageUrl && <img src={lastImageUrl} alt="Uploaded X-ray" style={{ marginTop: 12, width: "100%", maxWidth: 420, borderRadius: 10, border: "1px solid #ddd" }} />}

          {aiLoading && <p style={{ marginTop: 12 }}>Analyzing…</p>}

          {aiResult && (
            <div style={{ marginTop: 16, borderTop: "1px solid #eee", paddingTop: 16 }}>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Prediction: {aiResult.label}</div>
              <div style={{ color: "#444" }}>Confidence: {Math.round(aiResult.confidence * 100)}%</div>
              {aiResult.explanation && <div style={{ color: "#666", marginTop: 6 }}>{aiResult.explanation}</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
