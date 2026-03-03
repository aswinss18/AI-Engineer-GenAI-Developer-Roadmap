"use client";

import { useState, useRef, useEffect } from "react";

type Mode = "normal" | "stream" | "structured" | "search" | "document";

interface Message {
    role: "user" | "ai";
    content: string;
    /** For structured mode: parsed JSON */
    structured?: { summary: string; confidence: string | number };
    streaming?: boolean;
}

const LABELS: Record<Mode, { label: string; icon: string; color: string }> = {
    normal: { label: "Normal Chat", icon: "💬", color: "#4ade80" },
    stream: { label: "Streamed Chat", icon: "⚡", color: "#facc15" },
    structured: { label: "Structured Stream", icon: "🧠", color: "#818cf8" },
    search: { label: "FAISS Search", icon: "🔍", color: "#22c55e" },
    document: { label: "Document Chat", icon: "📄", color: "#f97316" },
};

interface ChatWindowProps {
    mode: Mode;
    onBack: () => void;
}

export default function ChatWindow({ mode, onBack }: ChatWindowProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [temperature, setTemperature] = useState(0.2);
    const [promptMode, setPromptMode] = useState<"default" | "summary" | "json">("default");
    const [deterministic, setDeterministic] = useState(false);
    const [documentUploaded, setDocumentUploaded] = useState(false);
    const [uploadingDoc, setUploadingDoc] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const sendMessage = async () => {
        const text = input.trim();
        if (!text || loading) return;

        const userMsg: Message = { role: "user", content: text };
        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setLoading(true);

        try {
            if (mode === "normal") {
                await handleNormal(text);
            } else if (mode === "stream") {
                await handleStream(text);
            } else if (mode === "search") {
                await handleSearch(text);
            } else if (mode === "document") {
                await handleDocumentChat(text);
            } else {
                await handleStructured(text);
            }
        } finally {
            setLoading(false);
        }
    };

    /* ── Normal: wait for full JSON response ── */
    async function handleNormal(text: string) {
        const payload = { message: text, temperature: deterministic ? 0 : temperature, mode: promptMode, deterministic };
        const res = await fetch(`/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        setMessages((prev) => [...prev, { role: "ai", content: data.response }]);
    }

    /* ── Streamed: token-by-token append ── */
    async function handleStream(text: string) {
        // Abort previous stream if any
        try {
            // store abort controller on window to survive re-renders
            (window as any).__chat_stream_abort?.abort?.();
        } catch {}
        const controller = new AbortController();
        (window as any).__chat_stream_abort = controller;

        const payload = { message: text, temperature: deterministic ? 0 : temperature, mode: promptMode, deterministic };
        const res = await fetch(`/api/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            signal: controller.signal,
        });
        const reader = res.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();

        // Add placeholder AI message and keep a small local buffer to reduce re-renders
        setMessages((prev) => [...prev, { role: "ai", content: "", streaming: true }]);

        let buffer = "";
        let lastFlush = performance.now();

        const flush = () => {
            if (!buffer) return;
            setMessages((prev) => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                last.content += buffer;
                updated[updated.length - 1] = last;
                return updated;
            });
            buffer = "";
            lastFlush = performance.now();
        };

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                // Flush at ~50ms intervals to batch updates for large responses
                if (performance.now() - lastFlush > 50) flush();
            }
        } catch (err) {
            // If aborted, continue to finalize
        } finally {
            // flush remainder and mark finished
            flush();
            setMessages((prev) => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                last.streaming = false;
                updated[updated.length - 1] = last;
                return updated;
            });
            try {
                reader.releaseLock?.();
            } catch {}
        }
    }

    /* ── Search: send query to faiss backend and render results ── */
    async function handleSearch(text: string) {
        // record the user message then ask backend
        const payload = { query: text };
        const res = await fetch(`/api/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            setMessages((prev) => [...prev, { role: "ai", content: "Error fetching search results" }]);
            return;
        }
        const data = await res.json();
        // format results into a string list
        const out = data.results
            ? data.results
                  .map((r: any, i: number) => `${i + 1}. ${r.text} (score: ${r.score})`)
                  .join("\n")
            : "(no results)";
        setMessages((prev) => [...prev, { role: "ai", content: out }]);
    }

    /* ── Document Chat: RAG pipeline with answer generation ── */
    async function handleDocumentChat(text: string) {
        const res = await fetch('http://localhost:8000/rag', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: text }),
        });
        
        if (!res.ok) {
            setMessages((prev) => [...prev, { role: "ai", content: "Error: Unable to process your question" }]);
            return;
        }
        
        const data = await res.json();
        
        // Just show the answer, not the sources
        const response = data.answer || "No answer generated.";
        
        setMessages((prev) => [...prev, { role: "ai", content: response }]);
    }

    /* ── Upload Document (File or Text) ── */
    const handleFileUpload = async (file: File) => {
        setUploadingDoc(true);
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const res = await fetch('http://localhost:8000/upload', {
                method: 'POST',
                body: formData,
            });
            
            if (res.ok) {
                const data = await res.json();
                setDocumentUploaded(true);
                setMessages([{ 
                    role: "ai", 
                    content: `✅ ${data.filename} uploaded and indexed successfully!\n\nDocument size: ${data.size} characters\n\nYou can now ask questions about the document.` 
                }]);
            } else {
                const error = await res.json();
                setMessages([{ role: "ai", content: `❌ Error: ${error.detail}` }]);
            }
        } catch (error) {
            setMessages([{ role: "ai", content: "❌ Error connecting to server. Make sure the backend is running on port 8000." }]);
        } finally {
            setUploadingDoc(false);
        }
    };

    const handleTextUpload = async (text: string) => {
        if (!text.trim()) return;
        
        setUploadingDoc(true);
        // Create a text file blob
        const blob = new Blob([text], { type: 'text/plain' });
        const file = new File([blob], 'document.txt', { type: 'text/plain' });
        await handleFileUpload(file);
    };

    /* ── Structured: stream + parse JSON on complete ── */
    async function handleStructured(text: string) {
        const payload = { prompt: text, deterministic };
        const res = await fetch(`/api/structured_stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const reader = res.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();
        let raw = "";
        let sseBuf = "";

        const aiMsg: Message = { role: "ai", content: "", streaming: true };
        setMessages((prev) => [...prev, aiMsg]);

        const flushChunk = (dataChunk: string) => {
            raw += dataChunk;
            setMessages((prev) => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                last.content = raw;
                updated[updated.length - 1] = last;
                return updated;
            });
        };

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            sseBuf += chunk;

            // split into complete SSE events (delimited by double newline)
            const parts = sseBuf.split(/\r?\n\r?\n/);
            sseBuf = parts.pop() || ""; // remainder

            for (const part of parts) {
                // collect 'data:' lines
                const lines = part.split(/\r?\n/);
                const dataLines: string[] = [];
                for (const line of lines) {
                    if (line.startsWith("data:")) {
                        dataLines.push(line.slice(5).trim());
                    }
                }
                if (dataLines.length === 0) continue;
                const data = dataLines.join("\n");
                flushChunk(data);

                // try parse JSON progressively; if valid JSON found, set structured and finish
                try {
                    const parsed = JSON.parse(raw);
                    const structured = {
                        summary: parsed.summary ?? raw,
                        confidence: parsed.confidence ?? "—",
                    };
                    setMessages((prev) => {
                        const updated = [...prev];
                        updated[updated.length - 1] = {
                            ...updated[updated.length - 1],
                            streaming: false,
                            structured,
                        };
                        return updated;
                    });
                    return;
                } catch {
                    // not complete JSON yet; continue streaming
                }
            }
        }

        // final attempt after stream ends
        if (sseBuf) {
            // process leftover buffer as a single event
            const lines = sseBuf.split(/\r?\n/);
            const dataLines: string[] = [];
            for (const line of lines) if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
            if (dataLines.length) flushChunk(dataLines.join("\n"));
        }

        try {
            const parsed = JSON.parse(raw);
            const structured = {
                summary: parsed.summary ?? raw,
                confidence: parsed.confidence ?? "—",
            };
            setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                    ...updated[updated.length - 1],
                    streaming: false,
                    structured,
                };
                return updated;
            });
        } catch {
            setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                    ...updated[updated.length - 1],
                    streaming: false,
                };
                return updated;
            });
        }
    }

    const { label, icon, color } = LABELS[mode];

    // Document upload screen
    if (mode === "document" && !documentUploaded) {
        return (
            <div
                style={{
                    minHeight: "100vh",
                    display: "flex",
                    flexDirection: "column",
                    maxWidth: "780px",
                    margin: "0 auto",
                    padding: "0 1rem",
                }}
            >
                {/* Header */}
                <div
                    className="glass"
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "1rem",
                        padding: "1rem 1.25rem",
                        margin: "1rem 0 0",
                        borderRadius: "var(--radius-lg)",
                    }}
                >
                    <button
                        onClick={onBack}
                        style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--muted)",
                            cursor: "pointer",
                            fontSize: "1.1rem",
                            padding: "0.25rem 0.6rem",
                            borderRadius: "8px",
                            transition: "color 0.15s, background 0.15s",
                        }}
                        onMouseEnter={(e) => {
                            (e.currentTarget as HTMLElement).style.color = "var(--fg)";
                            (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.06)";
                        }}
                        onMouseLeave={(e) => {
                            (e.currentTarget as HTMLElement).style.color = "var(--muted)";
                            (e.currentTarget as HTMLElement).style.background = "transparent";
                        }}
                    >
                        ← Back
                    </button>

                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flex: 1 }}>
                        <span style={{ fontSize: "1.3rem" }}>{icon}</span>
                        <span style={{ fontWeight: 700, fontSize: "1rem" }}>{label}</span>
                        <span
                            style={{
                                fontSize: "0.68rem",
                                padding: "0.15rem 0.55rem",
                                borderRadius: "9999px",
                                background: `${color}22`,
                                color,
                                border: `1px solid ${color}44`,
                                textTransform: "uppercase",
                                letterSpacing: "0.06em",
                                fontWeight: 600,
                            }}
                        >
                            RAG
                        </span>
                    </div>
                </div>

                {/* Upload Section */}
                <div
                    style={{
                        flex: 1,
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "center",
                        padding: "2rem 0",
                    }}
                >
                    <div
                        className="glass"
                        style={{
                            padding: "2rem",
                            borderRadius: "var(--radius-lg)",
                        }}
                    >
                        <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem" }}>
                            📄 Upload Your Document
                        </h2>
                        <p style={{ color: "var(--muted)", marginBottom: "1.5rem", lineHeight: 1.6 }}>
                            Upload a PDF or TXT file, or paste text directly. The document will be chunked, 
                            embedded, and indexed using FAISS for semantic search and RAG-based Q&A.
                        </p>
                        
                        {/* File Upload */}
                        <div style={{ marginBottom: "1.5rem" }}>
                            <label
                                style={{
                                    display: "block",
                                    width: "100%",
                                    padding: "2rem",
                                    background: "rgba(0,0,0,0.2)",
                                    border: "2px dashed var(--border)",
                                    borderRadius: "var(--radius-md)",
                                    textAlign: "center",
                                    cursor: "pointer",
                                    transition: "border-color 0.2s, background 0.2s",
                                }}
                                onDragOver={(e) => {
                                    e.preventDefault();
                                    (e.currentTarget as HTMLElement).style.borderColor = color;
                                    (e.currentTarget as HTMLElement).style.background = `${color}11`;
                                }}
                                onDragLeave={(e) => {
                                    (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                                    (e.currentTarget as HTMLElement).style.background = "rgba(0,0,0,0.2)";
                                }}
                                onDrop={(e) => {
                                    e.preventDefault();
                                    (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                                    (e.currentTarget as HTMLElement).style.background = "rgba(0,0,0,0.2)";
                                    const file = e.dataTransfer.files[0];
                                    if (file) handleFileUpload(file);
                                }}
                            >
                                <input
                                    type="file"
                                    accept=".txt,.pdf"
                                    onChange={(e) => {
                                        const file = e.target.files?.[0];
                                        if (file) handleFileUpload(file);
                                    }}
                                    disabled={uploadingDoc}
                                    style={{ display: "none" }}
                                />
                                <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>📁</div>
                                <div style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.25rem" }}>
                                    Click to browse or drag & drop
                                </div>
                                <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                                    Supports .txt and .pdf files
                                </div>
                            </label>
                        </div>

                        <div style={{ 
                            display: "flex", 
                            alignItems: "center", 
                            gap: "1rem", 
                            margin: "1.5rem 0",
                            color: "var(--muted)",
                            fontSize: "0.9rem"
                        }}>
                            <div style={{ flex: 1, height: "1px", background: "var(--border)" }} />
                            OR
                            <div style={{ flex: 1, height: "1px", background: "var(--border)" }} />
                        </div>
                        
                        {/* Text Paste */}
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Paste your document text here..."
                            disabled={uploadingDoc}
                            style={{
                                width: "100%",
                                minHeight: "200px",
                                padding: "1rem",
                                background: "rgba(0,0,0,0.2)",
                                border: "1px solid var(--border)",
                                borderRadius: "var(--radius-md)",
                                color: "var(--fg)",
                                fontSize: "0.9rem",
                                fontFamily: "inherit",
                                resize: "vertical",
                                marginBottom: "1rem",
                            }}
                        />
                        
                        <button
                            onClick={() => {
                                handleTextUpload(input);
                                setInput("");
                            }}
                            disabled={uploadingDoc || !input.trim()}
                            className="accent-btn"
                            style={{
                                width: "100%",
                                padding: "0.75rem",
                                fontSize: "1rem",
                                fontWeight: 600,
                            }}
                        >
                            {uploadingDoc ? "Uploading & Indexing..." : "Upload Text"}
                        </button>

                        {/* Sample text */}
                        <details style={{ marginTop: "1.5rem" }}>
                            <summary style={{ cursor: "pointer", color: "var(--muted)", fontSize: "0.9rem" }}>
                                Show sample document
                            </summary>
                            <pre
                                style={{
                                    marginTop: "0.75rem",
                                    padding: "1rem",
                                    background: "rgba(0,0,0,0.3)",
                                    borderRadius: "var(--radius-md)",
                                    fontSize: "0.8rem",
                                    overflow: "auto",
                                    maxHeight: "200px",
                                }}
                            >
{`Artificial Intelligence (AI) is transforming the world.
Machine learning is a subset of AI that enables computers to learn from data.

Natural Language Processing (NLP) allows computers to understand human language.
Deep learning uses neural networks with multiple layers.

Computer vision enables machines to interpret visual information.
Reinforcement learning trains agents through rewards and penalties.

AI applications include healthcare, finance, and autonomous vehicles.
Ethics in AI is becoming increasingly important as technology advances.`}
                            </pre>
                        </details>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div
            style={{
                minHeight: "100vh",
                display: "flex",
                flexDirection: "column",
                maxWidth: "780px",
                margin: "0 auto",
                padding: "0 1rem",
            }}
        >
            {/* Header */}
            <div
                className="glass"
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "1rem",
                    padding: "1rem 1.25rem",
                    margin: "1rem 0 0",
                    borderRadius: "var(--radius-lg)",
                    position: "sticky",
                    top: "1rem",
                    zIndex: 10,
                }}
            >
                <button
                    onClick={onBack}
                    style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--muted)",
                        cursor: "pointer",
                        fontSize: "1.1rem",
                        padding: "0.25rem 0.6rem",
                        borderRadius: "8px",
                        transition: "color 0.15s, background 0.15s",
                    }}
                    onMouseEnter={(e) => {
                        (e.currentTarget as HTMLElement).style.color = "var(--fg)";
                        (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.06)";
                    }}
                    onMouseLeave={(e) => {
                        (e.currentTarget as HTMLElement).style.color = "var(--muted)";
                        (e.currentTarget as HTMLElement).style.background = "transparent";
                    }}
                >
                    ← Back
                </button>

                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flex: 1 }}>
                    <span style={{ fontSize: "1.3rem" }}>{icon}</span>
                    <span style={{ fontWeight: 700, fontSize: "1rem" }}>{label}</span>
                    <span
                        style={{
                            fontSize: "0.68rem",
                            padding: "0.15rem 0.55rem",
                            borderRadius: "9999px",
                            background: `${color}22`,
                            color,
                            border: `1px solid ${color}44`,
                            textTransform: "uppercase",
                            letterSpacing: "0.06em",
                            fontWeight: 600,
                        }}
                    >
                        {mode}
                    </span>
                </div>

                {/* Status dot */}
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--muted)", fontSize: "0.8rem" }}>
                    <div
                        style={{
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            background: loading ? "#facc15" : "#4ade80",
                            boxShadow: loading ? "0 0 6px #facc15" : "0 0 6px #4ade80",
                            transition: "background 0.3s, box-shadow 0.3s",
                        }}
                    />
                    {loading ? "Thinking…" : "Ready"}
                </div>
            </div>

            {/* Control bar */}
            <div style={{ display: "flex", alignItems: "center", gap: "1rem", margin: "0.5rem 0" }}>
                <label style={{ fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                    Temp: {temperature.toFixed(1)}
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={temperature}
                        onChange={(e) => setTemperature(parseFloat(e.target.value))}
                        disabled={deterministic}
                    />
                </label>
                <label style={{ fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                    Prompt mode:
                    <select value={promptMode} onChange={(e) => setPromptMode(e.target.value as any)}>
                        <option value="default">Default</option>
                        <option value="summary">Summary</option>
                        <option value="json">JSON</option>
                    </select>
                </label>
                <label style={{ fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                    <input
                        type="checkbox"
                        checked={deterministic}
                        onChange={(e) => setDeterministic(e.target.checked)}
                    />
                    Deterministic
                </label>
            </div>

            {/* Message thread */}
            <div
                style={{
                    flex: 1,
                    overflowY: "auto",
                    padding: "1.5rem 0",
                    display: "flex",
                    flexDirection: "column",
                    gap: "1rem",
                }}
            >
                {messages.length === 0 && (
                    <div
                        style={{
                            flex: 1,
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            justifyContent: "center",
                            color: "var(--muted)",
                            gap: "0.75rem",
                            paddingTop: "4rem",
                        }}
                    >
                        <span style={{ fontSize: "3rem" }}>{icon}</span>
                        <p style={{ fontSize: "1rem" }}>Send a message to start chatting in <strong style={{ color: "var(--fg)" }}>{label}</strong> mode.</p>
                    </div>
                )}

                {messages.map((msg, i) => (
                    <div
                        key={i}
                        style={{
                            display: "flex",
                            justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                        }}
                    >
                        {msg.role === "user" ? (
                            <div
                                style={{
                                    maxWidth: "70%",
                                    background: "var(--user-bubble)",
                                    color: "#fff",
                                    borderRadius: "var(--radius-md) var(--radius-md) 4px var(--radius-md)",
                                    padding: "0.75rem 1rem",
                                    fontSize: "0.93rem",
                                    lineHeight: 1.6,
                                    wordBreak: "break-word",
                                }}
                            >
                                {msg.content}
                            </div>
                        ) : (
                            <div
                                className="glass"
                                style={{
                                    maxWidth: "75%",
                                    borderRadius: "var(--radius-md) var(--radius-md) var(--radius-md) 4px",
                                    padding: "0.875rem 1.1rem",
                                    fontSize: "0.93rem",
                                    lineHeight: 1.7,
                                    wordBreak: "break-word",
                                }}
                            >
                                {/* Structured mode: show parsed card when done, raw stream while streaming */}
                                {mode === "structured" && msg.structured ? (
                                    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                                        <p>{msg.structured.summary}</p>
                                        <div
                                            style={{
                                                display: "inline-flex",
                                                alignItems: "center",
                                                gap: "0.4rem",
                                                background: "rgba(129,140,248,0.12)",
                                                border: "1px solid rgba(129,140,248,0.3)",
                                                borderRadius: "9999px",
                                                padding: "0.25rem 0.75rem",
                                                fontSize: "0.8rem",
                                                color: "#818cf8",
                                                fontWeight: 600,
                                                width: "fit-content",
                                            }}
                                        >
                                            <span>confidence</span>
                                            <span style={{ fontWeight: 800 }}>{msg.structured.confidence}</span>
                                        </div>
                                    </div>
                                ) : (
                                    <>
                                        <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
                                        {msg.streaming && (
                                            <span
                                                style={{
                                                    display: "inline-block",
                                                    width: "2px",
                                                    height: "1em",
                                                    background: "var(--accent2)",
                                                    marginLeft: "2px",
                                                    verticalAlign: "middle",
                                                    animation: "blink 0.7s step-end infinite",
                                                }}
                                            />
                                        )}
                                    </>
                                )}
                            </div>
                        )}
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>

            {/* Input bar */}
            <div
                className="glass"
                style={{
                    display: "flex",
                    alignItems: "flex-end",
                    gap: "0.75rem",
                    padding: "0.875rem 1rem",
                    margin: "0 0 1.25rem",
                    borderRadius: "var(--radius-lg)",
                    position: "sticky",
                    bottom: "1rem",
                }}
            >
                <textarea
                    id="chat-input"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            sendMessage();
                        }
                    }}
                    placeholder={`${
    mode === "search" ? "Search query…" : `Message in ${label} mode… (Enter to send, Shift+Enter for newline)`
}`}
                    disabled={loading}
                    rows={1}
                    style={{
                        flex: 1,
                        background: "transparent",
                        border: "none",
                        outline: "none",
                        color: "var(--fg)",
                        fontSize: "0.93rem",
                        resize: "none",
                        lineHeight: 1.6,
                        maxHeight: "160px",
                        overflowY: "auto",
                    }}
                />
                <button
                    id="send-btn"
                    className="accent-btn"
                    onClick={sendMessage}
                    disabled={loading || !input.trim()}
                    style={{ flexShrink: 0, padding: "0.55rem 1.25rem", fontSize: "0.875rem" }}
                >
                    {loading ? "…" : "Send"}
                </button>
            </div>

            {/* Blinking cursor keyframe */}
            <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
      `}</style>
        </div>
    );
}
