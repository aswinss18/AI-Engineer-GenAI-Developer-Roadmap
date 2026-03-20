 "use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";

interface Message {
    role: "user" | "ai";
    content: string;
    streaming?: boolean;
    sources?: Array<{
        doc: string;
        page: number;
        text: string;
        combined_score?: number;
        search_types?: string[];
        hybrid_score?: number;
    }>;
    metadata?: {
        chunks_found: number;
        final_chunks?: number;
        prompt_tokens: number;
        completion_tokens: number;
        total_tokens: number;
        latency: number;
        pipeline_version?: string;
    };
    // Agent-specific fields
    tools_used?: number;
    tool_calls?: Array<{
        tool_name: string;
        arguments: any;
        result: any;
    }>;
    has_tool_calls?: boolean;
    react_pattern?: boolean;
    memory_used?: boolean;
    memory_context_info?: {
        memories_retrieved: number;
        memories_used: Array<{
            text: string;
            importance: number;
            confidence: string;
            combined_score: number;
        }>;
        system_stats: {
            total_memories: number;
            quality_score: number;
        };
    };
}

export default function PDFRagPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [documentUploaded, setDocumentUploaded] = useState(false);
    const [uploadingDoc, setUploadingDoc] = useState(false);
    const [processingDoc, setProcessingDoc] = useState(false);
    const [processingStatus, setProcessingStatus] = useState("");
    const [agentMode, setAgentMode] = useState(false);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [showSources, setShowSources] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);
    const router = useRouter();
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const clearAllDocuments = async () => {
        try {
            const res = await fetch('http://localhost:8000/documents/clear', {
                method: 'POST'
            });
            if (res.ok) {
                const data = await res.json();
                setMessages([{ 
                    role: "ai", 
                    content: `✅ ${data.message}\n\nAll documents have been cleared. You can now upload new PDFs to start fresh.` 
                }]);
            }
        } catch (error) {
            console.error('Clear documents error:', error);
            setMessages([{ 
                role: "ai", 
                content: "❌ Error clearing documents. Please check if the backend is running." 
            }]);
        }
    };

    const checkProcessingStatus = async () => {
        try {
            const res = await fetch('http://localhost:8000/status');
            if (res.ok) {
                const data = await res.json();
                if (data.documents_loaded > 0) {
                    setProcessingDoc(false);
                    setProcessingStatus("");
                    
                    if (data.multi_document_mode && data.unique_documents > 1) {
                        setMessages([{ 
                            role: "ai", 
                            content: `✅ PDF processed successfully!\n\n🔄 Multi-Document Mode Active!\n\nYou now have ${data.unique_documents} documents loaded:\n${data.document_names.map((name: string) => `• ${name}`).join('\n')}\n\nYou can ask questions that compare or synthesize information across all documents.` 
                        }]);
                    } else {
                        setMessages([{ 
                            role: "ai", 
                            content: `✅ PDF processed successfully!\n\nYour document is now ready for questions. You can ask anything about the content.` 
                        }]);
                    }
                    return true;
                } else {
                    setProcessingStatus(`Processing document... (${data.documents_loaded} chunks loaded)`);
                    return false;
                }
            }
        } catch (error) {
            console.error('Status check error:', error);
        }
        return false;
    };
    const sendMessage = async () => {
        const text = input.trim();
        if (!text || loading || processingDoc) return;

        const userMsg: Message = { role: "user", content: text };
        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setLoading(true);

        try {
            // Choose endpoint based on mode
            const endpoint = agentMode ? 'agent-stream' : 'ask-stream';
            const res = await fetch(`http://localhost:8000/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': agentMode ? 'application/json' : 'application/x-www-form-urlencoded' },
                body: agentMode 
                    ? JSON.stringify({ query: text, conversation_history: null })
                    : `question=${encodeURIComponent(text)}`,
            });
            
            if (!res.ok) {
                const errorText = await res.text();
                setMessages((prev) => [...prev, { role: "ai", content: `Error: ${res.status} - ${errorText}` }]);
                return;
            }
            
            // Add placeholder AI message for streaming
            setMessages((prev) => [...prev, { role: "ai", content: "", streaming: true }]);
            
            const reader = res.body?.getReader();
            if (!reader) return;
            
            const decoder = new TextDecoder();
            let buffer = "";
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;
                
                // Process complete SSE events
                const events = buffer.split('\n\n');
                buffer = events.pop() || '';
                
                for (const event of events) {
                    if (event.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(event.slice(6));
                            if (data.done) {
                                setMessages((prev) => {
                                    const updated = [...prev];
                                    const last = { ...updated[updated.length - 1] };
                                    last.streaming = false;
                                    updated[updated.length - 1] = last;
                                    return updated;
                                });
                            } else if (agentMode) {
                                if (data.type === "metadata") {
                                    setMessages((prev) => {
                                        const updated = [...prev];
                                        const last = { ...updated[updated.length - 1] };
                                        last.tools_used = data.tools_used;
                                        last.tool_calls = data.tool_calls;
                                        last.has_tool_calls = data.has_tool_calls;
                                        last.react_pattern = data.react_pattern;
                                        last.memory_used = data.memory_used;
                                        last.memory_context_info = data.memory_context_info;
                                        updated[updated.length - 1] = last;
                                        return updated;
                                    });
                                } else if (data.type === "content") {
                                    setMessages((prev) => {
                                        const updated = [...prev];
                                        const last = { ...updated[updated.length - 1] };
                                        last.content += data.content;
                                        updated[updated.length - 1] = last;
                                        return updated;
                                    });
                                } else if (data.type === "error") {
                                    setMessages((prev) => {
                                        const updated = [...prev];
                                        const last = { ...updated[updated.length - 1] };
                                        last.content = data.content;
                                        last.streaming = false;
                                        updated[updated.length - 1] = last;
                                        return updated;
                                    });
                                }
                            } else {
                                if (data.answer !== undefined) {
                                    setMessages((prev) => {
                                        const updated = [...prev];
                                        const last = { ...updated[updated.length - 1] };
                                        if (data.answer) {
                                            last.content += data.answer;
                                        }
                                        if (data.sources) {
                                            last.sources = data.sources;
                                        }
                                        if (data.metadata) {
                                            last.metadata = data.metadata;
                                        }
                                        updated[updated.length - 1] = last;
                                        return updated;
                                    });
                                }
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data:', e);
                        }
                    }
                }
            }
            
        } catch (error: any) {
            console.error('Fetch error:', error);
            setMessages((prev) => [...prev, { role: "ai", content: `Error connecting to server: ${error.message}` }]);
        } finally {
            setLoading(false);
        }
    };
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
                
                setProcessingDoc(true);
                setProcessingStatus("Processing document...");
                setMessages([{ 
                    role: "ai", 
                    content: `✅ PDF uploaded successfully!\n\n${data.message || 'Document is being processed in the background.'}\n\nPlease wait while we process your document...` 
                }]);
                
                // Poll for processing completion
                const pollInterval = setInterval(async () => {
                    const isComplete = await checkProcessingStatus();
                    if (isComplete) {
                        clearInterval(pollInterval);
                        setDocumentUploaded(true);
                    }
                }, 2000);
                
                // Timeout after 60 seconds
                setTimeout(() => {
                    clearInterval(pollInterval);
                    if (processingDoc) {
                        setProcessingDoc(false);
                        setProcessingStatus("");
                        setMessages([{ 
                            role: "ai", 
                            content: `⚠️ Processing is taking longer than expected. You can try asking questions now, but the document might not be fully indexed yet.` 
                        }]);
                        setDocumentUploaded(true);
                    }
                }, 60000);
                
            } else {
                const errorText = await res.text();
                setMessages([{ role: "ai", content: `❌ Error: ${errorText || 'Failed to upload PDF'}` }]);
            }
        } catch (error: any) {
            console.error('Upload error:', error);
            setMessages([{ role: "ai", content: "❌ Error connecting to server. Make sure the PDF RAG backend is running on port 8000." }]);
        } finally {
            setUploadingDoc(false);
        }
    };
    // Document upload screen
    if (!documentUploaded) {
        return (
            <div style={{
                minHeight: "100vh",
                display: "flex",
                flexDirection: "column",
                maxWidth: "600px",
                margin: "0 auto",
                padding: "2rem 1rem",
            }}>
                {/* Simple Header */}
                <div className="glass" style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "1rem",
                    padding: "1rem 1.5rem",
                    marginBottom: "2rem",
                    borderRadius: "var(--radius-lg)",
                }}>
                    <button
                        onClick={() => router.push("/")}
                        style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--muted)",
                            cursor: "pointer",
                            fontSize: "1rem",
                            padding: "0.5rem",
                            borderRadius: "8px",
                        }}
                    >
                        ← Back
                    </button>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <span style={{ fontSize: "1.5rem" }}>📚</span>
                        <span style={{ fontWeight: 700, fontSize: "1.1rem" }}>PDF Chat Assistant</span>
                    </div>
                </div>

                {/* Upload Section */}
                <div className="glass" style={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                    padding: "3rem 2rem",
                    borderRadius: "var(--radius-lg)",
                    textAlign: "center",
                }}>
                    <h2 style={{ fontSize: "1.8rem", fontWeight: 700, marginBottom: "1rem" }}>
                        Upload Your PDF
                    </h2>
                    <p style={{ color: "var(--muted)", marginBottom: "2rem", lineHeight: 1.6 }}>
                        Upload a PDF document to start chatting with it. Ask questions, get summaries, and explore the content with AI assistance.
                    </p>
                    
                    <label style={{
                        display: "block",
                        width: "100%",
                        padding: "3rem 2rem",
                        background: "rgba(0,0,0,0.2)",
                        border: "2px dashed var(--border)",
                        borderRadius: "var(--radius-lg)",
                        cursor: uploadingDoc ? "not-allowed" : "pointer",
                        transition: "all 0.2s",
                        marginBottom: "2rem",
                    }}
                    onDragOver={(e) => {
                        e.preventDefault();
                        if (!uploadingDoc) {
                            (e.currentTarget as HTMLElement).style.borderColor = "#e11d48";
                            (e.currentTarget as HTMLElement).style.background = "#e11d4811";
                        }
                    }}
                    onDragLeave={(e) => {
                        (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                        (e.currentTarget as HTMLElement).style.background = "rgba(0,0,0,0.2)";
                    }}
                    onDrop={(e) => {
                        e.preventDefault();
                        (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                        (e.currentTarget as HTMLElement).style.background = "rgba(0,0,0,0.2)";
                        if (!uploadingDoc) {
                            const file = e.dataTransfer.files[0];
                            if (file && file.type === 'application/pdf') {
                                handleFileUpload(file);
                            }
                        }
                    }}>
                        <input
                            type="file"
                            accept=".pdf"
                            onChange={(e) => {
                                const file = e.target.files?.[0];
                                if (file) handleFileUpload(file);
                            }}
                            disabled={uploadingDoc}
                            style={{ display: "none" }}
                        />
                        <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>
                            {uploadingDoc ? "⏳" : "📄"}
                        </div>
                        <div style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.5rem" }}>
                            {uploadingDoc ? "Uploading..." : "Click to browse or drag & drop"}
                        </div>
                        <div style={{ fontSize: "0.9rem", color: "var(--muted)" }}>
                            PDF files only
                        </div>
                    </label>

                    <div style={{ 
                        display: "grid", 
                        gridTemplateColumns: "repeat(3, 1fr)", 
                        gap: "1rem",
                        fontSize: "0.85rem",
                        color: "var(--muted)"
                    }}>
                        <div>🔍 Smart Search</div>
                        <div>🧠 AI Powered</div>
                        <div>⚡ Fast Processing</div>
                    </div>
                </div>
            </div>
        );
    }
    return (
        <div style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            maxWidth: "700px",
            margin: "0 auto",
            padding: "1rem",
        }}>
            {/* Clean Header */}
            <div className="glass" style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "1rem 1.5rem",
                marginBottom: "1rem",
                borderRadius: "var(--radius-lg)",
                position: "sticky",
                top: "1rem",
                zIndex: 10,
            }}>
                <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                    <button
                        onClick={() => router.push("/")}
                        style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--muted)",
                            cursor: "pointer",
                            fontSize: "1rem",
                            padding: "0.5rem",
                            borderRadius: "8px",
                        }}
                    >
                        ← Back
                    </button>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <span style={{ fontSize: "1.5rem" }}>📚</span>
                        <span style={{ fontWeight: 700, fontSize: "1.1rem" }}>PDF Chat</span>
                    </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                    {/* Mode Toggle */}
                    <button
                        onClick={() => setAgentMode(!agentMode)}
                        style={{
                            background: agentMode ? "rgba(34, 197, 94, 0.1)" : "rgba(225, 29, 72, 0.1)",
                            border: `1px solid ${agentMode ? "rgba(34, 197, 94, 0.3)" : "rgba(225, 29, 72, 0.3)"}`,
                            color: agentMode ? "#22c55e" : "#e11d48",
                            cursor: "pointer",
                            fontSize: "0.85rem",
                            padding: "0.5rem 1rem",
                            borderRadius: "var(--radius-md)",
                            fontWeight: 600,
                        }}
                    >
                        {agentMode ? "🤖 Agent" : "📄 RAG"}
                    </button>

                    {/* Status */}
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8rem", color: "var(--muted)" }}>
                        <div style={{
                            width: 6,
                            height: 6,
                            borderRadius: "50%",
                            background: processingDoc ? "#f59e0b" : loading ? "#facc15" : "#4ade80",
                        }} />
                        {processingDoc ? "Processing" : loading ? "Thinking" : "Ready"}
                    </div>

                    {/* Advanced Options */}
                    <button
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        style={{
                            background: "rgba(59, 130, 246, 0.1)",
                            border: "1px solid rgba(59, 130, 246, 0.3)",
                            color: "#3b82f6",
                            cursor: "pointer",
                            fontSize: "0.8rem",
                            padding: "0.4rem 0.8rem",
                            borderRadius: "var(--radius-md)",
                            fontWeight: 600,
                        }}
                    >
                        ⚙️ {showAdvanced ? "Hide" : "Options"}
                    </button>
                </div>
            </div>

            {/* Advanced Options Panel */}
            {showAdvanced && (
                <div className="glass" style={{
                    padding: "1rem",
                    marginBottom: "1rem",
                    borderRadius: "var(--radius-lg)",
                }}>
                    <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                        <button
                            onClick={() => {
                                setDocumentUploaded(false);
                                setProcessingDoc(false);
                                setProcessingStatus("");
                            }}
                            style={{
                                background: "rgba(225, 29, 72, 0.1)",
                                border: "1px solid rgba(225, 29, 72, 0.3)",
                                color: "#e11d48",
                                cursor: "pointer",
                                fontSize: "0.75rem",
                                padding: "0.4rem 0.8rem",
                                borderRadius: "var(--radius-sm)",
                                fontWeight: 600,
                            }}
                        >
                            📄 Add PDF
                        </button>
                        <button
                            onClick={clearAllDocuments}
                            style={{
                                background: "rgba(239, 68, 68, 0.1)",
                                border: "1px solid rgba(239, 68, 68, 0.3)",
                                color: "#ef4444",
                                cursor: "pointer",
                                fontSize: "0.75rem",
                                padding: "0.4rem 0.8rem",
                                borderRadius: "var(--radius-sm)",
                                fontWeight: 600,
                            }}
                        >
                            🗑️ Clear All
                        </button>
                        <button
                            onClick={() => setShowSources(!showSources)}
                            style={{
                                background: "rgba(139, 92, 246, 0.1)",
                                border: "1px solid rgba(139, 92, 246, 0.3)",
                                color: "#8b5cf6",
                                cursor: "pointer",
                                fontSize: "0.75rem",
                                padding: "0.4rem 0.8rem",
                                borderRadius: "var(--radius-sm)",
                                fontWeight: 600,
                            }}
                        >
                            📊 {showSources ? "Hide" : "Show"} Sources
                        </button>
                    </div>
                </div>
            )}
            {/* Message thread */}
            <div style={{
                flex: 1,
                overflowY: "auto",
                padding: "0 0 1rem",
                display: "flex",
                flexDirection: "column",
                gap: "1rem",
            }}>
                {messages.length === 0 && (
                    <div style={{
                        flex: 1,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "var(--muted)",
                        gap: "1rem",
                        padding: "4rem 2rem",
                        textAlign: "center",
                    }}>
                        <span style={{ fontSize: "4rem" }}>{agentMode ? "🤖" : "📚"}</span>
                        <div>
                            <h3 style={{ fontSize: "1.2rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--fg)" }}>
                                {agentMode ? "AI Agent Ready" : "PDF Chat Ready"}
                            </h3>
                            <p style={{ fontSize: "0.9rem", lineHeight: 1.5 }}>
                                {agentMode 
                                    ? "I can search documents, perform calculations, get weather info, and more."
                                    : "Ask questions about your PDF document content."
                                }
                            </p>
                        </div>
                        
                        <div style={{ 
                            display: "grid", 
                            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", 
                            gap: "0.5rem", 
                            width: "100%",
                            maxWidth: "500px",
                            marginTop: "1rem"
                        }}>
                            {(agentMode ? [
                                "What documents do I have?",
                                "Calculate 15% of 50000",
                                "Weather in Bangalore",
                                "Convert 100 USD to INR"
                            ] : [
                                "What is this document about?",
                                "Summarize the main points",
                                "What are the key findings?",
                                "Explain the methodology"
                            ]).map((suggestion, i) => (
                                <button
                                    key={i}
                                    onClick={() => setInput(suggestion)}
                                    style={{
                                        background: "rgba(225, 29, 72, 0.1)",
                                        border: "1px solid rgba(225, 29, 72, 0.2)",
                                        color: "var(--fg)",
                                        padding: "0.75rem 1rem",
                                        borderRadius: "var(--radius-md)",
                                        fontSize: "0.85rem",
                                        cursor: "pointer",
                                        transition: "all 0.15s",
                                        textAlign: "left",
                                    }}
                                    onMouseEnter={(e) => {
                                        (e.currentTarget as HTMLElement).style.background = "rgba(225, 29, 72, 0.15)";
                                        (e.currentTarget as HTMLElement).style.borderColor = "rgba(225, 29, 72, 0.3)";
                                    }}
                                    onMouseLeave={(e) => {
                                        (e.currentTarget as HTMLElement).style.background = "rgba(225, 29, 72, 0.1)";
                                        (e.currentTarget as HTMLElement).style.borderColor = "rgba(225, 29, 72, 0.2)";
                                    }}
                                >
                                    {suggestion}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
                {messages.map((msg, i) => (
                    <div key={i} style={{
                        display: "flex",
                        justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                    }}>
                        {msg.role === "user" ? (
                            <div style={{
                                maxWidth: "70%",
                                background: "var(--user-bubble)",
                                color: "#fff",
                                borderRadius: "var(--radius-lg) var(--radius-lg) 4px var(--radius-lg)",
                                padding: "1rem 1.25rem",
                                fontSize: "0.95rem",
                                lineHeight: 1.6,
                                wordBreak: "break-word",
                            }}>
                                {msg.content}
                            </div>
                        ) : (
                            <div className="glass" style={{
                                maxWidth: "85%",
                                borderRadius: "var(--radius-lg) var(--radius-lg) var(--radius-lg) 4px",
                                padding: "1rem 1.25rem",
                                fontSize: "0.95rem",
                                lineHeight: 1.7,
                                wordBreak: "break-word",
                            }}>
                                <div style={{ whiteSpace: "pre-wrap" }}>
                                    {msg.streaming && <span style={{ opacity: 0.6 }}>●</span>}
                                    {msg.content}
                                </div>

                                {/* Agent Mode Metadata */}
                                {agentMode && msg.tools_used !== undefined && (
                                    <div style={{
                                        marginTop: "1rem",
                                        padding: "0.75rem",
                                        background: "rgba(34, 197, 94, 0.1)",
                                        border: "1px solid rgba(34, 197, 94, 0.2)",
                                        borderRadius: "var(--radius-md)",
                                        fontSize: "0.8rem",
                                    }}>
                                        <div style={{ fontWeight: 600, marginBottom: "0.5rem", color: "#22c55e" }}>
                                            🤖 Agent Analysis
                                        </div>
                                        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                                            <span>🔧 Tools: {msg.tools_used}</span>
                                            {msg.react_pattern && <span>🧠 ReAct Pattern</span>}
                                            {msg.memory_used && <span>💭 Memory Used</span>}
                                        </div>
                                        
                                        {msg.memory_context_info && (
                                            <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "var(--muted)" }}>
                                                Retrieved {msg.memory_context_info.memories_retrieved} memories
                                                ({msg.memory_context_info.system_stats.total_memories} total)
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Sources */}
                                {showSources && msg.sources && msg.sources.length > 0 && (
                                    <div style={{
                                        marginTop: "1rem",
                                        padding: "0.75rem",
                                        background: "rgba(139, 92, 246, 0.1)",
                                        border: "1px solid rgba(139, 92, 246, 0.2)",
                                        borderRadius: "var(--radius-md)",
                                        fontSize: "0.8rem",
                                    }}>
                                        <div style={{ fontWeight: 600, marginBottom: "0.5rem", color: "#8b5cf6" }}>
                                            📊 Sources ({msg.sources.length})
                                        </div>
                                        {msg.sources.slice(0, 3).map((source, idx) => (
                                            <div key={idx} style={{ marginBottom: "0.5rem", fontSize: "0.75rem" }}>
                                                <div style={{ fontWeight: 600 }}>
                                                    {source.doc} (Page {source.page})
                                                </div>
                                                <div style={{ color: "var(--muted)", marginTop: "0.25rem" }}>
                                                    {source.text.substring(0, 100)}...
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Metadata */}
                                {showSources && msg.metadata && (
                                    <div style={{
                                        marginTop: "0.5rem",
                                        fontSize: "0.7rem",
                                        color: "var(--muted)",
                                        display: "flex",
                                        gap: "1rem",
                                        flexWrap: "wrap",
                                    }}>
                                        <span>⚡ {msg.metadata.latency}ms</span>
                                        <span>🔍 {msg.metadata.chunks_found} chunks</span>
                                        <span>🎯 {msg.metadata.total_tokens} tokens</span>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}
                
                {processingStatus && (
                    <div style={{
                        textAlign: "center",
                        color: "var(--muted)",
                        fontSize: "0.9rem",
                        padding: "1rem",
                    }}>
                        {processingStatus}
                    </div>
                )}
                
                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="glass" style={{
                padding: "1rem",
                borderRadius: "var(--radius-lg)",
                position: "sticky",
                bottom: "1rem",
            }}>
                <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-end" }}>
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                sendMessage();
                            }
                        }}
                        placeholder={agentMode ? "Ask me anything - I can search docs, calculate, get weather..." : "Ask about your PDF..."}
                        disabled={loading || processingDoc}
                        style={{
                            flex: 1,
                            background: "rgba(0,0,0,0.2)",
                            border: "1px solid var(--border)",
                            borderRadius: "var(--radius-md)",
                            padding: "0.75rem 1rem",
                            fontSize: "0.95rem",
                            color: "var(--fg)",
                            resize: "none",
                            minHeight: "44px",
                            maxHeight: "120px",
                            fontFamily: "inherit",
                        }}
                        rows={1}
                        onInput={(e) => {
                            const target = e.target as HTMLTextAreaElement;
                            target.style.height = "44px";
                            target.style.height = Math.min(target.scrollHeight, 120) + "px";
                        }}
                    />
                    <button
                        onClick={sendMessage}
                        disabled={!input.trim() || loading || processingDoc}
                        style={{
                            background: (!input.trim() || loading || processingDoc) 
                                ? "var(--muted)" 
                                : "var(--primary)",
                            border: "none",
                            borderRadius: "var(--radius-md)",
                            padding: "0.75rem 1.5rem",
                            color: "#fff",
                            cursor: (!input.trim() || loading || processingDoc) ? "not-allowed" : "pointer",
                            fontSize: "0.9rem",
                            fontWeight: 600,
                            minWidth: "80px",
                            height: "44px",
                        }}
                    >
                        {loading ? "..." : "Send"}
                    </button>
                </div>
            </div>
        </div>
    );
}