import { useState, useCallback, useRef } from "react";

const API_BASE = "http://localhost:8001";

const STATUS_CONFIG = {
  cease:       { label: "Cease & Desist", color: "#059669", bg: "#f0fdf4", border: "#6ee7b7", icon: "✓"  },
  irrelevant:  { label: "Irrelevant",     color: "#dc2626", bg: "#fef2f2", border: "#fca5a5", icon: "⛔" },
  uncertain:   { label: "Needs Review",   color: "#d97706", bg: "#fffbeb", border: "#fcd34d", icon: "⚠"  },
  hitl_needed: { label: "Needs Review",   color: "#7c3aed", bg: "#faf5ff", border: "#c4b5fd", icon: "👤" },
  error:       { label: "Error",          color: "#6b7280", bg: "#f9fafb", border: "#d1d5db", icon: "!"  },
};

function ConfidenceBar({ score }) {
  if (!score) return null;
  const color = score >= 85 ? "#059669" : score >= 60 ? "#d97706" : "#dc2626";
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: "#6b7280", fontFamily: "monospace" }}>CONFIDENCE</span>
        <span style={{ fontSize: 11, fontWeight: 700, color, fontFamily: "monospace" }}>{score}%</span>
      </div>
      <div style={{ height: 4, background: "#e5e7eb", borderRadius: 999, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${score}%`, background: color, borderRadius: 999, transition: "width 0.8s ease" }} />
      </div>
    </div>
  );
}

function HitlModal({ doc, onSubmit, onClose }) {
  const [decision,   setDecision]   = useState("");
  const [reason,     setReason]     = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError,  setFormError]  = useState("");

  const handleSubmit = async () => {
    if (!decision) { setFormError("Please select Cease & Desist or Irrelevant."); return; }
    if (decision === "irrelevant" && !reason.trim()) { setFormError("Please provide a reason for marking as irrelevant."); return; }
    setSubmitting(true);
    setFormError("");
    try {
      await onSubmit(doc.document_name, decision, reason.trim());
    } catch (e) {
      setFormError(e.message || "Submission failed. Please try again.");
      setSubmitting(false);
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: 20 }}>
      <div style={{ background: "#fff", borderRadius: 16, width: "100%", maxWidth: 560, padding: 28, maxHeight: "90vh", overflowY: "auto" }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
          <div>
            <span style={{ display: "inline-block", background: "#faf5ff", color: "#7c3aed", fontSize: 10, fontWeight: 700, padding: "3px 10px", borderRadius: 6, fontFamily: "monospace", marginBottom: 8 }}>
              HUMAN REVIEW REQUIRED
            </span>
            <div style={{ fontWeight: 700, fontSize: 16, color: "#111" }}>{doc.document_name}</div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 22, color: "#9ca3af", cursor: "pointer", padding: "0 4px", marginLeft: 12 }}>×</button>
        </div>

        {/* LLM suggestion */}
        <div style={{ background: "#fffbeb", border: "1px solid #fcd34d", borderRadius: 10, padding: "14px 16px", marginBottom: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: "#92400e", fontWeight: 600 }}>
              LLM suggested: <span style={{ textTransform: "uppercase" }}>{doc.suggested || doc.classification || "unknown"}</span>
            </span>
            {doc.confidence_score > 0 && (
              <span style={{ fontSize: 12, fontFamily: "monospace", color: "#d97706", fontWeight: 700 }}>{doc.confidence_score}% confidence</span>
            )}
          </div>
          {doc.reason && <div style={{ fontSize: 12, color: "#78350f", lineHeight: 1.5 }}>{doc.reason}</div>}
          {doc.preview && (
            <div style={{ marginTop: 10, padding: "8px 12px", background: "#fff", borderRadius: 6, fontSize: 11, color: "#6b7280", fontFamily: "monospace", lineHeight: 1.6, maxHeight: 90, overflow: "hidden", borderLeft: "3px solid #fcd34d" }}>
              {doc.preview}…
            </div>
          )}
        </div>

        {/* Step 1 — Classification */}
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 11, color: "#6b7280", fontFamily: "monospace", fontWeight: 600, marginBottom: 10, letterSpacing: "0.05em" }}>
            STEP 1 — SELECT CLASSIFICATION
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <button
              onClick={() => { setDecision("cease"); setFormError(""); }}
              style={{ padding: "16px 14px", borderRadius: 10, cursor: "pointer", border: decision === "cease" ? "2px solid #059669" : "1.5px solid #e5e7eb", background: decision === "cease" ? "#f0fdf4" : "#fff", textAlign: "left", transition: "all 0.15s" }}
            >
              <div style={{ fontSize: 22, marginBottom: 6 }}>⛔</div>
              <div style={{ fontWeight: 700, fontSize: 13, color: "#059669", marginBottom: 3 }}>Cease & Desist</div>
              <div style={{ fontSize: 11, color: "#9ca3af", lineHeight: 1.4 }}>Valid C&D request — stored in database</div>
            </button>
            <button
              onClick={() => { setDecision("irrelevant"); setFormError(""); }}
              style={{ padding: "16px 14px", borderRadius: 10, cursor: "pointer", border: decision === "irrelevant" ? "2px solid #dc2626" : "1.5px solid #e5e7eb", background: decision === "irrelevant" ? "#fef2f2" : "#fff", textAlign: "left", transition: "all 0.15s" }}
            >
              <div style={{ fontSize: 22, marginBottom: 6 }}>✓</div>
              <div style={{ fontWeight: 700, fontSize: 13, color: "#dc2626", marginBottom: 3 }}>Irrelevant</div>
              <div style={{ fontSize: 11, color: "#9ca3af", lineHeight: 1.4 }}>Not a C&D document — will be archived</div>
            </button>
          </div>
        </div>

        {/* Step 2 — Reason */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, color: "#6b7280", fontFamily: "monospace", fontWeight: 600, marginBottom: 8, letterSpacing: "0.05em" }}>
            STEP 2 — PROVIDE REASON
            {decision === "irrelevant" && <span style={{ color: "#dc2626", marginLeft: 4 }}>* required</span>}
            {decision === "cease"      && <span style={{ color: "#9ca3af",  marginLeft: 4 }}>(optional)</span>}
            {!decision                 && <span style={{ color: "#9ca3af",  marginLeft: 4 }}>(select classification first)</span>}
          </div>
          <textarea
            value={reason}
            onChange={e => { setReason(e.target.value); setFormError(""); }}
            disabled={!decision}
            placeholder={
              decision === "irrelevant" ? "e.g. This is a vendor invoice for software services, not a legal demand letter"
              : decision === "cease"    ? "e.g. Clear C&D from attorney demanding stop of trademark use (optional)"
              : "Select a classification above first..."
            }
            rows={3}
            style={{ width: "100%", padding: "10px 12px", borderRadius: 8, fontSize: 13, border: `1.5px solid ${formError && decision === "irrelevant" && !reason.trim() ? "#fca5a5" : "#e5e7eb"}`, fontFamily: "inherit", resize: "vertical", color: "#374151", lineHeight: 1.5, background: !decision ? "#f9fafb" : "#fff", outline: "none" }}
          />
        </div>

        {formError && (
          <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#dc2626", marginBottom: 16 }}>
            {formError}
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!decision || submitting}
          style={{ width: "100%", padding: "14px", background: submitting || !decision ? "#e5e7eb" : decision === "cease" ? "#059669" : "#dc2626", color: submitting || !decision ? "#9ca3af" : "#fff", border: "none", borderRadius: 10, fontSize: 14, fontWeight: 700, cursor: !decision || submitting ? "not-allowed" : "pointer", fontFamily: "inherit", transition: "all 0.2s" }}
        >
          {submitting ? (
            <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
              <span style={{ width: 14, height: 14, border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "#fff", borderRadius: "50%", display: "inline-block", animation: "spin 0.8s linear infinite" }} />
              Submitting decision…
            </span>
          ) : !decision ? "Select a classification to continue"
            : decision === "cease" ? "✓  Confirm as Cease & Desist"
            : "✓  Confirm as Irrelevant"
          }
        </button>

      </div>
    </div>
  );
}

function ResultCard({ result, index, onReview }) {
  const [expanded, setExpanded] = useState(false);
  const isHitlPending = result.hitl_pending && !result.human_reviewed;
  const cfg = STATUS_CONFIG[result.classification] || STATUS_CONFIG.uncertain;

  return (
    <div style={{ background: "#fff", border: isHitlPending ? "2px solid #c4b5fd" : `1px solid ${cfg.border}`, borderRadius: 12, overflow: "hidden", animation: `slideIn 0.3s ease ${index * 0.06}s both` }}>
      <div onClick={() => setExpanded(e => !e)} style={{ padding: "14px 18px", cursor: "pointer", display: "flex", alignItems: "center", gap: 12, background: cfg.bg, borderBottom: expanded ? `1px solid ${cfg.border}` : "none" }}>
        <span style={{ fontSize: 18, lineHeight: 1 }}>{cfg.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 14, color: "#111", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{result.document_name}</div>
          <div style={{ fontSize: 12, color: cfg.color, fontWeight: 500, marginTop: 2, display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            {cfg.label}
            {result.human_reviewed  && <span style={{ fontSize: 10, background: "#f3e8ff", color: "#7c3aed", padding: "1px 7px", borderRadius: 999, fontWeight: 700 }}>HUMAN REVIEWED</span>}
            {result.duplicate_detected && <span style={{ fontSize: 10, background: "#fef3c7", color: "#d97706", padding: "1px 7px", borderRadius: 999, fontWeight: 700 }}>DUPLICATE</span>}
          </div>
        </div>
        {isHitlPending && (
          <button
            onClick={e => { e.stopPropagation(); onReview(result); }}
            style={{ background: "#7c3aed", color: "#fff", border: "none", borderRadius: 8, padding: "7px 14px", fontSize: 12, fontWeight: 700, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap", flexShrink: 0 }}
          >
            Review →
          </button>
        )}
        {result.confidence_score > 0 && !isHitlPending && (
          <div style={{ fontSize: 13, fontWeight: 700, color: cfg.color, fontFamily: "monospace", minWidth: 42, textAlign: "right" }}>{result.confidence_score}%</div>
        )}
        <span style={{ color: "#9ca3af", fontSize: 11, flexShrink: 0, transform: expanded ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}>▼</span>
      </div>

      {expanded && (
        <div style={{ padding: "16px 18px" }}>
          {result.error ? (
            <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#dc2626" }}>{result.error}</div>
          ) : (
            <>
              <ConfidenceBar score={result.confidence_score} />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 20px", marginTop: 14 }}>
                {[["Sender", result.sender_name], ["Address", result.sender_address], ["Activity", result.cease_activity], ["Action", result.action_taken]]
                  .filter(([, v]) => v && v !== "unknown" && v !== "none")
                  .map(([label, value]) => (
                    <div key={label}>
                      <div style={{ fontSize: 10, color: "#9ca3af", fontFamily: "monospace", marginBottom: 3 }}>{label.toUpperCase()}</div>
                      <div style={{ fontSize: 13, color: "#374151", lineHeight: 1.4 }}>{value}</div>
                    </div>
                  ))}
              </div>
              {result.reason && (
                <div style={{ marginTop: 14, padding: "10px 14px", background: "#f8fafc", borderRadius: 8, borderLeft: `3px solid ${cfg.border}` }}>
                  <div style={{ fontSize: 10, color: "#9ca3af", fontFamily: "monospace", marginBottom: 4 }}>CLASSIFICATION REASON</div>
                  <div style={{ fontSize: 13, color: "#374151", lineHeight: 1.5 }}>{result.reason}</div>
                </div>
              )}
              {result.irrelevant_reason && (
                <div style={{ marginTop: 10, padding: "10px 14px", background: "#fef2f2", borderRadius: 8, borderLeft: "3px solid #fca5a5" }}>
                  <div style={{ fontSize: 10, color: "#9ca3af", fontFamily: "monospace", marginBottom: 4 }}>WHY IRRELEVANT</div>
                  <div style={{ fontSize: 13, color: "#374151", lineHeight: 1.5 }}>{result.irrelevant_reason}</div>
                </div>
              )}
              {isHitlPending && (
                <div style={{ marginTop: 14, padding: "12px 14px", background: "#faf5ff", border: "1px solid #c4b5fd", borderRadius: 8, display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 18 }}>👤</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "#7c3aed" }}>Awaiting your review</div>
                    <div style={{ fontSize: 12, color: "#6d28d9", marginTop: 2 }}>Click "Review →" in the card header to classify this document</div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function StatsBar({ results }) {
  const c = { total: results.length, cease: 0, irrelevant: 0, pending: 0 };
  results.forEach(r => {
    if (r.hitl_pending && !r.human_reviewed) { c.pending++; return; }
    if (r.classification === "cease")      c.cease++;
    if (r.classification === "irrelevant") c.irrelevant++;
  });
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 20 }}>
      {[["Total", c.total, "#374151"], ["Cease & Desist", c.cease, "#059669"], ["Irrelevant", c.irrelevant, "#dc2626"], ["Needs Review", c.pending, "#7c3aed"]].map(([label, value, color]) => (
        <div key={label} style={{ background: "#fff", borderRadius: 10, padding: "12px 14px", border: "1px solid #e5e7eb", textAlign: "center" }}>
          <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>{label}</div>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [files,      setFiles]      = useState([]);
  const [dragging,   setDragging]   = useState(false);
  const [processing, setProcessing] = useState(false);
  const [results,    setResults]    = useState([]);
  const [pageError,  setPageError]  = useState(null);
  const [hitlDoc,    setHitlDoc]    = useState(null);
  const inputRef = useRef();

  const pendingCount = results.filter(r => r.hitl_pending && !r.human_reviewed).length;

  const addFiles = useCallback((incoming) => {
    const pdfs = Array.from(incoming).filter(f => f.name.toLowerCase().endsWith(".pdf"));
    if (!pdfs.length) { setPageError("Only PDF files are accepted."); return; }
    setPageError(null);
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name));
      return [...prev, ...pdfs.filter(f => !existing.has(f.name))];
    });
  }, []);

  const onDrop = useCallback((e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files); }, [addFiles]);

  const handleProcess = async () => {
    if (!files.length) return;
    setProcessing(true); setResults([]); setPageError(null);
    const form = new FormData();
    files.forEach(f => form.append("files", f));
    try {
      const resp = await fetch(`${API_BASE}/process`, { method: "POST", body: form });
      if (!resp.ok) throw new Error(`Server error ${resp.status}: ${await resp.text()}`);
      const data = await resp.json();
      setResults([
        ...data.results,
        ...(data.error_details || []).map(e => ({ document_name: e.filename, classification: "error", error: e.error, hitl_pending: false, human_reviewed: false })),
      ]);
    } catch (err) {
      setPageError(err.message || "Failed to connect. Is the server running on port 8001?");
    } finally {
      setProcessing(false);
    }
  };

  const handleHitlSubmit = async (docName, decision, reason) => {
    const resp = await fetch(`${API_BASE}/hitl-decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_name: docName, decision, reason }),
    });
    if (!resp.ok) throw new Error(`Server error ${resp.status}: ${await resp.text()}`);
    const updated = await resp.json();
    setResults(prev => prev.map(r => r.document_name === docName ? { ...updated, hitl_pending: false, human_reviewed: true } : r));
    setHitlDoc(null);
  };

  const openReview = async (result) => {
    try {
      const resp = await fetch(`${API_BASE}/hitl-pending`);
      if (resp.ok) {
        const data = await resp.json();
        const fresh = data.documents?.find(d => d.document_name === result.document_name);
        if (fresh) { setHitlDoc(fresh); return; }
      }
    } catch (_) {}
    setHitlDoc({ document_name: result.document_name, suggested: result.classification, confidence_score: result.confidence_score, reason: result.reason, preview: "" });
  };

  const reset = () => { setFiles([]); setResults([]); setPageError(null); };

  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", fontFamily: "'DM Sans','Segoe UI',sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
        @keyframes slideIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:none} }
        @keyframes spin    { to{transform:rotate(360deg)} }
        @keyframes pulse   { 0%,100%{opacity:1} 50%{opacity:0.4} }
        * { box-sizing:border-box; margin:0; padding:0; }
      `}</style>

      {hitlDoc && <HitlModal doc={hitlDoc} onSubmit={handleHitlSubmit} onClose={() => setHitlDoc(null)} />}

      {/* Header */}
      <div style={{ background: "#fff", borderBottom: "1px solid #e5e7eb", padding: "0 28px", height: 60, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 34, height: 34, background: "#dc2626", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 17 }}>⛔</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: "#111" }}>C&D Processor</div>
            <div style={{ fontSize: 11, color: "#9ca3af" }}>Cease & Desist Document Intelligence</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {pendingCount > 0 && (
            <div style={{ background: "#faf5ff", border: "1px solid #c4b5fd", borderRadius: 8, padding: "4px 12px", fontSize: 12, color: "#7c3aed", fontWeight: 600, animation: "pulse 2s infinite" }}>
              {pendingCount} awaiting review
            </div>
          )}
          <div style={{ fontSize: 11, fontFamily: "monospace", color: "#9ca3af", background: "#f1f5f9", padding: "4px 10px", borderRadius: 6 }}>
            Groq · LangGraph · llama-3.3-70b
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 780, margin: "0 auto", padding: "28px 20px" }}>

        {results.length === 0 ? (
          <>
            <div
              onDrop={onDrop} onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
              onClick={() => inputRef.current?.click()}
              style={{ border: `2px dashed ${dragging ? "#dc2626" : "#d1d5db"}`, borderRadius: 16, padding: "52px 32px", textAlign: "center", background: dragging ? "#fff5f5" : "#fff", cursor: "pointer", transition: "all 0.2s", marginBottom: 20 }}
            >
              <input ref={inputRef} type="file" multiple accept=".pdf" style={{ display: "none" }} onChange={e => addFiles(e.target.files)} />
              <div style={{ fontSize: 42, marginBottom: 14 }}>📄</div>
              <div style={{ fontWeight: 700, fontSize: 16, color: "#111", marginBottom: 6 }}>Drop PDFs here to process</div>
              <div style={{ fontSize: 13, color: "#9ca3af" }}>Or click to browse · Multiple files supported</div>
            </div>

            {files.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 11, color: "#6b7280", fontFamily: "monospace", marginBottom: 10 }}>{files.length} FILE{files.length !== 1 ? "S" : ""} QUEUED</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {files.map(f => (
                    <div key={f.name} style={{ display: "flex", alignItems: "center", gap: 10, background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "10px 14px" }}>
                      <span style={{ fontSize: 16 }}>📑</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 500, color: "#111", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{f.name}</div>
                        <div style={{ fontSize: 11, color: "#9ca3af" }}>{(f.size / 1024).toFixed(0)} KB</div>
                      </div>
                      <button onClick={() => setFiles(p => p.filter(x => x.name !== f.name))} style={{ background: "none", border: "none", cursor: "pointer", color: "#9ca3af", fontSize: 20, padding: 4, lineHeight: 1 }}>×</button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {pageError && <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 10, padding: "12px 16px", marginBottom: 16, fontSize: 13, color: "#dc2626" }}>{pageError}</div>}

            <button onClick={handleProcess} disabled={!files.length || processing} style={{ width: "100%", padding: "15px", background: files.length && !processing ? "#dc2626" : "#e5e7eb", color: files.length && !processing ? "#fff" : "#9ca3af", border: "none", borderRadius: 12, fontSize: 15, fontWeight: 700, cursor: files.length && !processing ? "pointer" : "not-allowed", transition: "all 0.2s", fontFamily: "inherit" }}>
              {processing ? (
                <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
                  <span style={{ width: 16, height: 16, border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "#fff", borderRadius: "50%", display: "inline-block", animation: "spin 0.8s linear infinite" }} />
                  Processing {files.length} document{files.length !== 1 ? "s" : ""}…
                </span>
              ) : `Process ${files.length || ""} Document${files.length !== 1 ? "s" : ""}`}
            </button>

            {processing && (
              <div style={{ textAlign: "center", marginTop: 14 }}>
                <div style={{ fontSize: 12, color: "#9ca3af", fontFamily: "monospace", animation: "pulse 1.5s infinite" }}>
                  Groq vision extracting · llama-3.3-70b classifying · Please wait…
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 18, color: "#111" }}>Processing Results</div>
                <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 3 }}>
                  {results.length} document{results.length !== 1 ? "s" : ""} processed{pendingCount > 0 && ` · ${pendingCount} awaiting your review`}
                </div>
              </div>
              <button onClick={reset} style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8, padding: "8px 16px", fontSize: 13, color: "#374151", cursor: "pointer", fontFamily: "inherit", fontWeight: 500 }}>← Process more</button>
            </div>

            {pendingCount > 0 && (
              <div style={{ background: "#faf5ff", border: "2px solid #c4b5fd", borderRadius: 12, padding: "14px 18px", marginBottom: 20, display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 22 }}>👤</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14, color: "#7c3aed" }}>{pendingCount} document{pendingCount !== 1 ? "s need" : " needs"} your review</div>
                  <div style={{ fontSize: 12, color: "#6d28d9", marginTop: 2 }}>Click the purple <strong>"Review →"</strong> button on each card to classify it</div>
                </div>
              </div>
            )}

            <StatsBar results={results} />

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {results.map((r, i) => <ResultCard key={`${r.document_name}-${i}`} result={r} index={i} onReview={openReview} />)}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
