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
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: agentMode ? `query=${encodeURIComponent(text)}` : `question=${encodeURIComponent(text)}`,
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

    const checkProcessingStatus = async () => {
        try {
            const res = await fetch('http://localhost:8000/status');
            if (res.ok) {
                const data = await res.json();
                if (data.documents_loaded > 0) {
                    setProcessingDoc(false);
                    setProcessingStatus("");
                    
                    // Show multi-document status if applicable
                    if (data.multi_document_mode && data.unique_documents > 1) {
                        setMessages([{ 
                            role: "ai", 
                            content: `✅ PDF processed successfully!\n\n🔄 Multi-Document Mode Active!\n\nYou now have ${data.unique_documents} documents loaded:\n${data.document_names.map((name: string) => `• ${name}`).join('\n')}\n\nYou can ask questions that compare or synthesize information across all documents.` 
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
                            content: `✅ PDF processed successfully!\n\n🔄 Multi-Document Mode Active!\n\nYou now have ${data.unique_documents} documents loaded. You can ask questions that compare or synthesize information across all documents.` 
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
                    }}
                    onMouseEnter={(e) => {
                        (e.currentTarget as HTMLElement).style.background = "rgba(225, 29, 72, 0.15)";
                        (e.currentTarget as HTMLElement).style.borderColor = "rgba(225, 29, 72, 0.4)";
                    }}
                    onMouseLeave={(e) => {
                        (e.currentTarget as HTMLElement).style.background = "rgba(225, 29, 72, 0.1)";
                        (e.currentTarget as HTMLElement).style.borderColor = "rgba(225, 29, 72, 0.3)";
                    }}
                >
                    📄 Add PDF
                </button>


            </div>


                <div
                    className="glass"
                    style={{
                        margin: "0.5rem 0 0",
                        padding: "1rem",
                        borderRadius: "var(--radius-lg)",
                    }}
                >
                    <div style={{ 
                        display: "flex", 
                        alignItems: "center", 
                        justifyContent: "space-between",
                        marginBottom: "1rem"
                    }}>
                        <h3 style={{ 
                            fontSize: "0.9rem", 
                            fontWeight: 600, 
                            color: "var(--fg)",
                            margin: 0,
                            display: "flex",
                            alignItems: "center",
                            gap: "0.5rem"
                        }}>
                            💾 System Management
                        </h3>
                        <button
                            onClick={() => {
                                checkPersistenceStatus();
                                checkMemoryStatus();
                                if (showDetailedMemory) {
                                    checkDetailedMemoryInfo();
                                }
                            }}
                            style={{
                                background: "transparent",
                                border: "1px solid var(--border)",
                                color: "var(--muted)",
                                cursor: "pointer",
                                fontSize: "0.75rem",
                                padding: "0.25rem 0.5rem",
                                borderRadius: "var(--radius-sm)",
                                transition: "all 0.15s",
                            }}
                            onMouseEnter={(e) => {
                                (e.currentTarget as HTMLElement).style.color = "var(--fg)";
                                (e.currentTarget as HTMLElement).style.borderColor = "var(--accent2)";
                            }}
                            onMouseLeave={(e) => {
                                (e.currentTarget as HTMLElement).style.color = "var(--muted)";
                                (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                            }}
                        >
                            🔄 Refresh
                        </button>
                    </div>

                    {persistenceStatus ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                            {/* Status Grid */}
                            <div style={{ 
                                display: "grid", 
                                gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", 
                                gap: "0.5rem",
                                fontSize: "0.75rem"
                            }}>
                                <div style={{
                                    background: "rgba(0,0,0,0.2)",
                                    border: "1px solid var(--border)",
                                    borderRadius: "var(--radius-sm)",
                                    padding: "0.5rem",
                                    textAlign: "center"
                                }}>
                                    <div style={{ 
                                        color: persistenceStatus.validation_status === "healthy" ? "#4ade80" : "#f87171", 
                                        fontWeight: 600 
                                    }}>
                                        {persistenceStatus.validation_status === "healthy" ? "✅" : "❌"}
                                    </div>
                                    <div style={{ color: "var(--muted)" }}>Status</div>
                                </div>
                                <div style={{
                                    background: "rgba(0,0,0,0.2)",
                                    border: "1px solid var(--border)",
                                    borderRadius: "var(--radius-sm)",
                                    padding: "0.5rem",
                                    textAlign: "center"
                                }}>
                                    <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                        {persistenceStatus.loaded_document_count || 0}
                                    </div>
                                    <div style={{ color: "var(--muted)" }}>Documents</div>
                                </div>
                                <div style={{
                                    background: "rgba(0,0,0,0.2)",
                                    border: "1px solid var(--border)",
                                    borderRadius: "var(--radius-sm)",
                                    padding: "0.5rem",
                                    textAlign: "center"
                                }}>
                                    <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                        {persistenceStatus.cache_files || 0}
                                    </div>
                                    <div style={{ color: "var(--muted)" }}>Cache Files</div>
                                </div>
                                <div style={{
                                    background: "rgba(0,0,0,0.2)",
                                    border: "1px solid var(--border)",
                                    borderRadius: "var(--radius-sm)",
                                    padding: "0.5rem",
                                    textAlign: "center"
                                }}>
                                    <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                        {persistenceStatus.last_save_time ? 
                                            new Date(persistenceStatus.last_save_time).toLocaleTimeString() : 
                                            "Never"
                                        }
                                    </div>
                                    <div style={{ color: "var(--muted)" }}>Last Save</div>
                                </div>
                            </div>

                            {/* Actions */}
                            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
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
                                        transition: "all 0.15s",
                                        fontWeight: 600,
                                    }}
                                    onMouseEnter={(e) => {
                                        (e.currentTarget as HTMLElement).style.background = "rgba(239, 68, 68, 0.15)";
                                        (e.currentTarget as HTMLElement).style.borderColor = "rgba(239, 68, 68, 0.4)";
                                    }}
                                    onMouseLeave={(e) => {
                                        (e.currentTarget as HTMLElement).style.background = "rgba(239, 68, 68, 0.1)";
                                        (e.currentTarget as HTMLElement).style.borderColor = "rgba(239, 68, 68, 0.3)";
                                    }}
                                >
                                    🗑️ Clear All Documents
                                </button>
                            </div>

                            {/* Error display */}
                            {persistenceStatus.error && (
                                <div style={{
                                    background: "rgba(239, 68, 68, 0.1)",
                                    border: "1px solid rgba(239, 68, 68, 0.3)",
                                    borderRadius: "var(--radius-sm)",
                                    padding: "0.75rem",
                                    fontSize: "0.8rem",
                                    color: "#ef4444"
                                }}>
                                    <strong>Error:</strong> {persistenceStatus.error}
                                </div>
                            )}
                        </div>
                    ) : (
                        <div style={{ 
                            textAlign: "center", 
                            color: "var(--muted)", 
                            fontSize: "0.85rem",
                            padding: "1rem"
                        }}>
                            Loading persistence status...
                        </div>
                    )}

                    {/* Memory Management Section */}
                    <div style={{ 
                        borderTop: "1px solid var(--border)", 
                        paddingTop: "1rem", 
                        marginTop: "1rem" 
                    }}>
                        <h4 style={{ 
                            fontSize: "0.85rem", 
                            fontWeight: 600, 
                            color: "var(--fg)",
                            margin: "0 0 0.75rem 0",
                            display: "flex",
                            alignItems: "center",
                            gap: "0.5rem"
                        }}>
                            🧠 Agent Memory System
                        </h4>

                        {memoryStatus ? (
                            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                                {/* Memory Stats Grid */}
                                <div style={{ 
                                    display: "grid", 
                                    gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))", 
                                    gap: "0.5rem",
                                    fontSize: "0.75rem"
                                }}>
                                    <div style={{
                                        background: "rgba(0,0,0,0.2)",
                                        border: "1px solid var(--border)",
                                        borderRadius: "var(--radius-sm)",
                                        padding: "0.5rem",
                                        textAlign: "center"
                                    }}>
                                        <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                            {memoryStatus.chat_history_length || 0}
                                        </div>
                                        <div style={{ color: "var(--muted)" }}>Chat History</div>
                                    </div>
                                    <div style={{
                                        background: "rgba(0,0,0,0.2)",
                                        border: "1px solid var(--border)",
                                        borderRadius: "var(--radius-sm)",
                                        padding: "0.5rem",
                                        textAlign: "center"
                                    }}>
                                        <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                            {memoryStatus.stored_memories || 0}
                                        </div>
                                        <div style={{ color: "var(--muted)" }}>Stored Facts</div>
                                    </div>
                                    <div style={{
                                        background: "rgba(0,0,0,0.2)",
                                        border: "1px solid var(--border)",
                                        borderRadius: "var(--radius-sm)",
                                        padding: "0.5rem",
                                        textAlign: "center"
                                    }}>
                                        <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                            {memoryStatus.average_importance ? memoryStatus.average_importance.toFixed(2) : "0.00"}
                                        </div>
                                        <div style={{ color: "var(--muted)" }}>Avg Importance</div>
                                    </div>
                                    <div style={{
                                        background: "rgba(0,0,0,0.2)",
                                        border: "1px solid var(--border)",
                                        borderRadius: "var(--radius-sm)",
                                        padding: "0.5rem",
                                        textAlign: "center"
                                    }}>
                                        <div style={{ 
                                            color: memoryStatus.scoring_system === "advanced_ranking_enabled" ? "#4ade80" : "#f87171", 
                                            fontWeight: 600 
                                        }}>
                                            {memoryStatus.scoring_system === "advanced_ranking_enabled" ? "✅" : "❌"}
                                        </div>
                                        <div style={{ color: "var(--muted)" }}>Advanced Scoring</div>
                                    </div>
                                    <div style={{
                                        background: "rgba(0,0,0,0.2)",
                                        border: "1px solid var(--border)",
                                        borderRadius: "var(--radius-sm)",
                                        padding: "0.5rem",
                                        textAlign: "center"
                                    }}>
                                        <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                            {memoryStatus.average_access_count ? memoryStatus.average_access_count.toFixed(1) : "0.0"}
                                        </div>
                                        <div style={{ color: "var(--muted)" }}>Avg Access</div>
                                    </div>
                                    <div style={{
                                        background: "rgba(0,0,0,0.2)",
                                        border: "1px solid var(--border)",
                                        borderRadius: "var(--radius-sm)",
                                        padding: "0.5rem",
                                        textAlign: "center"
                                    }}>
                                        <div style={{ 
                                            color: memoryStatus.confidence_distribution?.high > 0 ? "#4ade80" : 
                                                   memoryStatus.confidence_distribution?.medium > 0 ? "#fbbf24" : "#f87171",
                                            fontWeight: 600 
                                        }}>
                                            {memoryStatus.confidence_distribution?.high || 0}H/{memoryStatus.confidence_distribution?.medium || 0}M/{memoryStatus.confidence_distribution?.low || 0}L
                                        </div>
                                        <div style={{ color: "var(--muted)" }}>Confidence</div>
                                    </div>
                                </div>

                                {/* Detailed Memory Analytics */}
                                <div style={{ 
                                    background: "rgba(0,0,0,0.1)",
                                    border: "1px solid var(--border)",
                                    borderRadius: "var(--radius-sm)",
                                    padding: "0.75rem",
                                    fontSize: "0.75rem"
                                }}>
                                    <div style={{ 
                                        fontWeight: 600, 
                                        color: "var(--fg)", 
                                        marginBottom: "0.5rem",
                                        display: "flex",
                                        alignItems: "center",
                                        gap: "0.5rem"
                                    }}>
                                        📊 Memory Quality Analytics
                                    </div>
                                    
                                    {/* Importance Distribution */}
                                    {memoryStatus.importance_distribution && (
                                        <div style={{ marginBottom: "0.5rem" }}>
                                            <div style={{ color: "var(--muted)", marginBottom: "0.25rem" }}>
                                                Importance Distribution:
                                            </div>
                                            <div style={{ display: "flex", gap: "0.75rem", fontSize: "0.7rem" }}>
                                                <div style={{ 
                                                    display: "flex", 
                                                    alignItems: "center", 
                                                    gap: "0.25rem",
                                                    background: "rgba(74, 222, 128, 0.1)",
                                                    padding: "0.25rem 0.5rem",
                                                    borderRadius: "var(--radius-sm)",
                                                    border: "1px solid rgba(74, 222, 128, 0.2)"
                                                }}>
                                                    <span style={{ color: "#4ade80", fontWeight: 600 }}>●</span>
                                                    <span style={{ color: "var(--fg)" }}>
                                                        High: {memoryStatus.importance_distribution.high || 0}
                                                    </span>
                                                </div>
                                                <div style={{ 
                                                    display: "flex", 
                                                    alignItems: "center", 
                                                    gap: "0.25rem",
                                                    background: "rgba(251, 191, 36, 0.1)",
                                                    padding: "0.25rem 0.5rem",
                                                    borderRadius: "var(--radius-sm)",
                                                    border: "1px solid rgba(251, 191, 36, 0.2)"
                                                }}>
                                                    <span style={{ color: "#fbbf24", fontWeight: 600 }}>●</span>
                                                    <span style={{ color: "var(--fg)" }}>
                                                        Medium: {memoryStatus.importance_distribution.medium || 0}
                                                    </span>
                                                </div>
                                                <div style={{ 
                                                    display: "flex", 
                                                    alignItems: "center", 
                                                    gap: "0.25rem",
                                                    background: "rgba(248, 113, 113, 0.1)",
                                                    padding: "0.25rem 0.5rem",
                                                    borderRadius: "var(--radius-sm)",
                                                    border: "1px solid rgba(248, 113, 113, 0.2)"
                                                }}>
                                                    <span style={{ color: "#f87171", fontWeight: 600 }}>●</span>
                                                    <span style={{ color: "var(--fg)" }}>
                                                        Low: {memoryStatus.importance_distribution.low || 0}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Access Frequency Distribution */}
                                    {memoryStatus.access_frequency_distribution && (
                                        <div style={{ marginBottom: "0.5rem" }}>
                                            <div style={{ color: "var(--muted)", marginBottom: "0.25rem" }}>
                                                Access Frequency:
                                            </div>
                                            <div style={{ display: "flex", gap: "0.75rem", fontSize: "0.7rem" }}>
                                                <span style={{ color: "#4ade80" }}>
                                                    Frequent: {memoryStatus.access_frequency_distribution.frequent || 0}
                                                </span>
                                                <span style={{ color: "#fbbf24" }}>
                                                    Occasional: {memoryStatus.access_frequency_distribution.occasional || 0}
                                                </span>
                                                <span style={{ color: "#f87171" }}>
                                                    Rare: {memoryStatus.access_frequency_distribution.rare || 0}
                                                </span>
                                            </div>
                                        </div>
                                    )}

                                    {/* Age Distribution */}
                                    {memoryStatus.age_distribution && (
                                        <div style={{ marginBottom: "0.5rem" }}>
                                            <div style={{ color: "var(--muted)", marginBottom: "0.25rem" }}>
                                                Memory Age:
                                            </div>
                                            <div style={{ display: "flex", gap: "0.75rem", fontSize: "0.7rem" }}>
                                                <span style={{ color: "#4ade80" }}>
                                                    Recent: {memoryStatus.age_distribution.recent || 0}
                                                </span>
                                                <span style={{ color: "#fbbf24" }}>
                                                    Old: {memoryStatus.age_distribution.old || 0}
                                                </span>
                                                <span style={{ color: "#f87171" }}>
                                                    Very Old: {memoryStatus.age_distribution.very_old || 0}
                                                </span>
                                            </div>
                                        </div>
                                    )}

                                    {/* Memory Quality Score */}
                                    {memoryStatus.importance_distribution && memoryStatus.stored_memories > 0 && (
                                        <div style={{ 
                                            marginTop: "0.5rem",
                                            paddingTop: "0.5rem",
                                            borderTop: "1px solid var(--border)"
                                        }}>
                                            <div style={{ color: "var(--muted)", marginBottom: "0.25rem" }}>
                                                Memory Quality Score:
                                            </div>
                                            {(() => {
                                                const total = memoryStatus.stored_memories;
                                                const high = memoryStatus.importance_distribution.high || 0;
                                                const medium = memoryStatus.importance_distribution.medium || 0;
                                                const qualityScore = total > 0 ? ((high * 1.0 + medium * 0.6) / total * 100) : 0;
                                                const qualityColor = qualityScore >= 80 ? "#4ade80" : 
                                                                   qualityScore >= 60 ? "#fbbf24" : "#f87171";
                                                const qualityLabel = qualityScore >= 80 ? "Excellent" :
                                                                    qualityScore >= 60 ? "Good" : "Needs Improvement";
                                                
                                                return (
                                                    <div style={{ 
                                                        display: "flex", 
                                                        alignItems: "center", 
                                                        gap: "0.5rem",
                                                        fontSize: "0.8rem"
                                                    }}>
                                                        <div style={{
                                                            background: `${qualityColor}20`,
                                                            border: `1px solid ${qualityColor}40`,
                                                            color: qualityColor,
                                                            padding: "0.25rem 0.5rem",
                                                            borderRadius: "var(--radius-sm)",
                                                            fontWeight: 600
                                                        }}>
                                                            {qualityScore.toFixed(1)}% {qualityLabel}
                                                        </div>
                                                        <div style={{ color: "var(--muted)", fontSize: "0.7rem" }}>
                                                            Based on importance distribution
                                                        </div>
                                                    </div>
                                                );
                                            })()}
                                        </div>
                                    )}
                                </div>

                                {/* Memory Actions */}
                                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                                    <button
                                        onClick={clearChatMemory}
                                        style={{
                                            background: "rgba(251, 191, 36, 0.1)",
                                            border: "1px solid rgba(251, 191, 36, 0.3)",
                                            color: "#fbbf24",
                                            cursor: "pointer",
                                            fontSize: "0.7rem",
                                            padding: "0.3rem 0.6rem",
                                            borderRadius: "var(--radius-sm)",
                                            transition: "all 0.15s",
                                            fontWeight: 600,
                                        }}
                                        onMouseEnter={(e) => {
                                            (e.currentTarget as HTMLElement).style.background = "rgba(251, 191, 36, 0.15)";
                                        }}
                                        onMouseLeave={(e) => {
                                            (e.currentTarget as HTMLElement).style.background = "rgba(251, 191, 36, 0.1)";
                                        }}
                                    >
                                        💬 Clear Chat
                                    </button>
                                    <button
                                        onClick={cleanupOldMemories}
                                        style={{
                                            background: "rgba(59, 130, 246, 0.1)",
                                            border: "1px solid rgba(59, 130, 246, 0.3)",
                                            color: "#3b82f6",
                                            cursor: "pointer",
                                            fontSize: "0.7rem",
                                            padding: "0.3rem 0.6rem",
                                            borderRadius: "var(--radius-sm)",
                                            transition: "all 0.15s",
                                            fontWeight: 600,
                                        }}
                                        onMouseEnter={(e) => {
                                            (e.currentTarget as HTMLElement).style.background = "rgba(59, 130, 246, 0.15)";
                                        }}
                                        onMouseLeave={(e) => {
                                            (e.currentTarget as HTMLElement).style.background = "rgba(59, 130, 246, 0.1)";
                                        }}
                                    >
                                        🧹 Cleanup Old
                                    </button>
                                    <button
                                        onClick={clearAllMemory}
                                        style={{
                                            background: "rgba(239, 68, 68, 0.1)",
                                            border: "1px solid rgba(239, 68, 68, 0.3)",
                                            color: "#ef4444",
                                            cursor: "pointer",
                                            fontSize: "0.7rem",
                                            padding: "0.3rem 0.6rem",
                                            borderRadius: "var(--radius-sm)",
                                            transition: "all 0.15s",
                                            fontWeight: 600,
                                        }}
                                        onMouseEnter={(e) => {
                                            (e.currentTarget as HTMLElement).style.background = "rgba(239, 68, 68, 0.15)";
                                        }}
                                        onMouseLeave={(e) => {
                                            (e.currentTarget as HTMLElement).style.background = "rgba(239, 68, 68, 0.1)";
                                        }}
                                    >
                                        🗑️ Clear All Memory
                                    </button>
                                    <button
                                        onClick={() => {
                                            setShowDetailedMemory(!showDetailedMemory);
                                            if (!showDetailedMemory) {
                                                checkDetailedMemoryInfo();
                                            }
                                        }}
                                        style={{
                                            background: "rgba(139, 92, 246, 0.1)",
                                            border: "1px solid rgba(139, 92, 246, 0.3)",
                                            color: "#8b5cf6",
                                            cursor: "pointer",
                                            fontSize: "0.7rem",
                                            padding: "0.3rem 0.6rem",
                                            borderRadius: "var(--radius-sm)",
                                            transition: "all 0.15s",
                                            fontWeight: 600,
                                        }}
                                        onMouseEnter={(e) => {
                                            (e.currentTarget as HTMLElement).style.background = "rgba(139, 92, 246, 0.15)";
                                        }}
                                        onMouseLeave={(e) => {
                                            (e.currentTarget as HTMLElement).style.background = "rgba(139, 92, 246, 0.1)";
                                        }}
                                    >
                                        {showDetailedMemory ? "🔼 Hide Details" : "🔽 Show Details"}
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div style={{ 
                                textAlign: "center", 
                                color: "var(--muted)", 
                                fontSize: "0.8rem",
                                padding: "0.5rem"
                            }}>
                                Loading memory status...
                            </div>
                        )}
                    </div>

                    {/* Detailed Memory Panel */}
                    {showDetailedMemory && detailedMemoryInfo && (
                        <div style={{ 
                            borderTop: "1px solid var(--border)", 
                            paddingTop: "1rem", 
                            marginTop: "1rem" 
                        }}>
                            <h4 style={{ 
                                fontSize: "0.85rem", 
                                fontWeight: 600, 
                                color: "var(--fg)",
                                margin: "0 0 0.75rem 0",
                                display: "flex",
                                alignItems: "center",
                                gap: "0.5rem"
                            }}>
                                🔍 Detailed Memory Analysis
                            </h4>

                            {/* System Health */}
                            <div style={{ 
                                background: "rgba(0,0,0,0.1)",
                                border: "1px solid var(--border)",
                                borderRadius: "var(--radius-sm)",
                                padding: "0.75rem",
                                marginBottom: "0.75rem",
                                fontSize: "0.75rem"
                            }}>
                                <div style={{ 
                                    fontWeight: 600, 
                                    color: "var(--fg)", 
                                    marginBottom: "0.5rem",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "0.5rem"
                                }}>
                                    ⚡ System Health
                                </div>
                                <div style={{ display: "flex", gap: "1rem", fontSize: "0.7rem" }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                                        <span style={{ 
                                            color: detailedMemoryInfo.system_health?.system_status === "healthy" ? "#4ade80" : "#f87171",
                                            fontWeight: 600 
                                        }}>
                                            {detailedMemoryInfo.system_health?.system_status === "healthy" ? "✅" : "❌"}
                                        </span>
                                        <span>Status: {detailedMemoryInfo.system_health?.system_status || "unknown"}</span>
                                    </div>
                                    <div>
                                        Quality: {(detailedMemoryInfo.system_health?.average_quality * 100 || 0).toFixed(1)}%
                                    </div>
                                    <div>
                                        Index Size: {detailedMemoryInfo.system_health?.index_size || 0}
                                    </div>
                                </div>
                            </div>

                            {/* Recent Memories */}
                            {detailedMemoryInfo.recent_memories && detailedMemoryInfo.recent_memories.length > 0 && (
                                <div style={{ 
                                    background: "rgba(0,0,0,0.1)",
                                    border: "1px solid var(--border)",
                                    borderRadius: "var(--radius-sm)",
                                    padding: "0.75rem",
                                    fontSize: "0.75rem"
                                }}>
                                    <div style={{ 
                                        fontWeight: 600, 
                                        color: "var(--fg)", 
                                        marginBottom: "0.5rem",
                                        display: "flex",
                                        alignItems: "center",
                                        gap: "0.5rem"
                                    }}>
                                        📝 Recent Memories ({detailedMemoryInfo.recent_memories.length})
                                    </div>
                                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                                        {detailedMemoryInfo.recent_memories.map((memory: any, index: number) => (
                                            <div key={index} style={{
                                                background: "rgba(0,0,0,0.2)",
                                                border: "1px solid var(--border)",
                                                borderRadius: "var(--radius-sm)",
                                                padding: "0.5rem",
                                                fontSize: "0.7rem"
                                            }}>
                                                <div style={{ 
                                                    display: "flex", 
                                                    justifyContent: "space-between", 
                                                    alignItems: "flex-start",
                                                    marginBottom: "0.25rem"
                                                }}>
                                                    <div style={{ 
                                                        color: "var(--fg)", 
                                                        fontWeight: 500,
                                                        flex: 1,
                                                        marginRight: "0.5rem"
                                                    }}>
                                                        {memory.text}
                                                    </div>
                                                    <div style={{ 
                                                        display: "flex", 
                                                        gap: "0.25rem",
                                                        flexShrink: 0
                                                    }}>
                                                        {/* Importance Badge */}
                                                        <span style={{
                                                            background: memory.importance >= 0.8 ? "rgba(74, 222, 128, 0.2)" :
                                                                       memory.importance >= 0.6 ? "rgba(251, 191, 36, 0.2)" : "rgba(248, 113, 113, 0.2)",
                                                            color: memory.importance >= 0.8 ? "#4ade80" :
                                                                   memory.importance >= 0.6 ? "#fbbf24" : "#f87171",
                                                            padding: "0.1rem 0.3rem",
                                                            borderRadius: "3px",
                                                            fontSize: "0.65rem",
                                                            fontWeight: 600
                                                        }}>
                                                            {memory.importance.toFixed(2)}
                                                        </span>
                                                        {/* Confidence Badge */}
                                                        <span style={{
                                                            background: memory.confidence === "high" ? "rgba(34, 197, 94, 0.2)" :
                                                                       memory.confidence === "medium" ? "rgba(251, 191, 36, 0.2)" : "rgba(248, 113, 113, 0.2)",
                                                            color: memory.confidence === "high" ? "#22c55e" :
                                                                   memory.confidence === "medium" ? "#fbbf24" : "#f87171",
                                                            padding: "0.1rem 0.3rem",
                                                            borderRadius: "3px",
                                                            fontSize: "0.65rem",
                                                            fontWeight: 600
                                                        }}>
                                                            {memory.confidence}
                                                        </span>
                                                    </div>
                                                </div>
                                                <div style={{ 
                                                    display: "flex", 
                                                    gap: "0.5rem", 
                                                    color: "var(--muted)",
                                                    fontSize: "0.65rem"
                                                }}>
                                                    <span>Type: {memory.type}</span>
                                                    <span>Access: {memory.access_count}x</span>
                                                    <span>Age: {memory.age_days.toFixed(1)}d</span>
                                                    <span>Source: {memory.source}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
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
                                <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
                                {msg.streaming && (
                                    <span style={{
                                        display: "inline-block",
                                        width: "2px",
                                        height: "1em",
                                        background: "var(--accent2)",
                                        marginLeft: "2px",
                                        verticalAlign: "middle",
                                        animation: "blink 0.7s step-end infinite",
                                    }} />
                                )}
                                
                                {/* Simple Tool Indicator */}
                                {msg.tool_calls && msg.tool_calls.length > 0 && !msg.streaming && (
                                    <div style={{ 
                                        marginTop: "1rem", 
                                        paddingTop: "1rem", 
                                        borderTop: "1px solid var(--border)",
                                    }}>
                                        <div style={{ 
                                            fontSize: "0.8rem", 
                                            color: "var(--muted)",
                                            marginBottom: "0.5rem",
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "0.5rem"
                                        }}>
                                            🛠️ Used {msg.tools_used} tool{msg.tools_used !== 1 ? 's' : ''}
                                            {msg.memory_used && (
                                                <span style={{ 
                                                    fontSize: "0.7rem", 
                                                    color: "#f59e0b",
                                                    background: "rgba(245, 158, 11, 0.1)",
                                                    padding: "0.1rem 0.4rem",
                                                    borderRadius: "4px"
                                                }}>
                                                    💾 Memory
                                                </span>
                                            )}
                                        </div>
                                        
                                        {showAdvanced && (
                                            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                                                {msg.tool_calls.map((toolCall, idx) => (
                                                    <div key={idx} style={{
                                                        background: "rgba(34, 197, 94, 0.1)",
                                                        border: "1px solid rgba(34, 197, 94, 0.2)",
                                                        borderRadius: "var(--radius-sm)",
                                                        padding: "0.5rem",
                                                        fontSize: "0.8rem",
                                                    }}>
                                                        <div style={{ 
                                                            fontWeight: 600, 
                                                            color: "#22c55e",
                                                            marginBottom: "0.25rem"
                                                        }}>
                                                            {toolCall.tool_name}
                                                        </div>
                                                        <div style={{ 
                                                            color: "var(--muted)", 
                                                            fontSize: "0.75rem"
                                                        }}>
                                                            {toolCall.result.success 
                                                                ? (toolCall.result.message || toolCall.result.answer || "Success")
                                                                : (toolCall.result.error || "Failed")
                                                            }
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                                
                                {/* Simple Sources */}
                                {msg.sources && msg.sources.length > 0 && !msg.streaming && showSources && (
                                    <div style={{ 
                                        marginTop: "1rem", 
                                        paddingTop: "1rem", 
                                        borderTop: "1px solid var(--border)",
                                    }}>
                                        <div style={{ 
                                            fontSize: "0.8rem", 
                                            fontWeight: 600, 
                                            color: "var(--muted)",
                                            marginBottom: "0.5rem"
                                        }}>
                                            📚 Sources ({msg.sources.length})
                                        </div>
                                        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                                            {msg.sources.slice(0, 3).map((source, idx) => (
                                                <div key={idx} style={{
                                                    background: "rgba(0,0,0,0.2)",
                                                    border: "1px solid var(--border)",
                                                    borderRadius: "var(--radius-sm)",
                                                    padding: "0.5rem",
                                                    fontSize: "0.75rem",
                                                }}>
                                                    <div style={{ 
                                                        fontWeight: 600, 
                                                        color: "var(--accent2)",
                                                        marginBottom: "0.25rem"
                                                    }}>
                                                        {source.doc} - Page {source.page}
                                                    </div>
                                                    <div style={{ 
                                                        color: "var(--muted)", 
                                                        lineHeight: 1.4
                                                    }}>
                                                        {source.text.length > 150 
                                                            ? source.text.substring(0, 150) + "..."
                                                            : source.text
                                                        }
                                                    </div>
                                                </div>
                                            ))}
                                            {msg.sources.length > 3 && (
                                                <div style={{ 
                                                    fontSize: "0.75rem", 
                                                    color: "var(--muted)",
                                                    textAlign: "center",
                                                    padding: "0.5rem"
                                                }}>
                                                    ... and {msg.sources.length - 3} more sources
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {/* Simple Metadata */}
                                {msg.metadata && !msg.streaming && showAdvanced && (
                                    <div style={{ 
                                        marginTop: "1rem", 
                                        paddingTop: "1rem", 
                                        borderTop: "1px solid var(--border)",
                                        fontSize: "0.75rem",
                                        color: "var(--muted)"
                                    }}>
                                        📊 {msg.metadata.total_tokens.toLocaleString()} tokens • {msg.metadata.latency}ms
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>
                                                        fontWeight: 600,
                                                        display: "flex",
                                                        alignItems: "center",
                                                        gap: "0.5rem"
                                                    }}>
                                                        💾 Memory Used
                                                        <span style={{
                                                            fontSize: "0.65rem",
                                                            color: "#d97706",
                                                            background: "rgba(217, 119, 6, 0.1)",
                                                            padding: "0.1rem 0.3rem",
                                                            borderRadius: "3px",
                                                            fontWeight: 500
                                                        }}>
                                                            High Confidence
                                                        </span>
                                                        {msg.memory_context_info && (
                                                            <span style={{
                                                                fontSize: "0.65rem",
                                                                color: "#059669",
                                                                background: "rgba(5, 150, 105, 0.1)",
                                                                padding: "0.1rem 0.3rem",
                                                                borderRadius: "3px",
                                                                fontWeight: 500
                                                            }}>
                                                                {msg.memory_context_info.memories_retrieved} Retrieved
                                                            </span>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {/* Memory Context Information */}
                                        {msg.memory_context_info && msg.memory_context_info.memories_used.length > 0 && (
                                            <div style={{
                                                background: "rgba(245, 158, 11, 0.05)",
                                                border: "1px solid rgba(245, 158, 11, 0.2)",
                                                borderRadius: "var(--radius-sm)",
                                                padding: "0.75rem",
                                                marginBottom: "0.75rem",
                                                fontSize: "0.75rem"
                                            }}>
                                                <div style={{ 
                                                    fontWeight: 600, 
                                                    color: "#f59e0b", 
                                                    marginBottom: "0.5rem",
                                                    display: "flex",
                                                    alignItems: "center",
                                                    justifyContent: "space-between"
                                                }}>
                                                    <span>🧠 Memory Context Used</span>
                                                    <div style={{ display: "flex", gap: "0.5rem", fontSize: "0.65rem" }}>
                                                        <span style={{
                                                            background: "rgba(34, 197, 94, 0.1)",
                                                            color: "#22c55e",
                                                            padding: "0.1rem 0.3rem",
                                                            borderRadius: "3px",
                                                            fontWeight: 600
                                                        }}>
                                                            Quality: {msg.memory_context_info.system_stats.quality_score.toFixed(1)}%
                                                        </span>
                                                        <span style={{
                                                            background: "rgba(59, 130, 246, 0.1)",
                                                            color: "#3b82f6",
                                                            padding: "0.1rem 0.3rem",
                                                            borderRadius: "3px",
                                                            fontWeight: 600
                                                        }}>
                                                            Total: {msg.memory_context_info.system_stats.total_memories}
                                                        </span>
                                                    </div>
                                                </div>
                                                
                                                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                                                    {msg.memory_context_info.memories_used.map((memory: any, idx: number) => (
                                                        <div key={idx} style={{
                                                            background: "rgba(0,0,0,0.1)",
                                                            border: "1px solid var(--border)",
                                                            borderRadius: "var(--radius-sm)",
                                                            padding: "0.5rem",
                                                            fontSize: "0.7rem"
                                                        }}>
                                                            <div style={{ 
                                                                display: "flex", 
                                                                justifyContent: "space-between", 
                                                                alignItems: "flex-start",
                                                                marginBottom: "0.25rem"
                                                            }}>
                                                                <div style={{ 
                                                                    color: "var(--fg)", 
                                                                    fontWeight: 500,
                                                                    flex: 1,
                                                                    marginRight: "0.5rem"
                                                                }}>
                                                                    {memory.text}
                                                                </div>
                                                                <div style={{ 
                                                                    display: "flex", 
                                                                    gap: "0.25rem",
                                                                    flexShrink: 0
                                                                }}>
                                                                    {/* Combined Score Badge */}
                                                                    <span style={{
                                                                        background: memory.combined_score >= 0.8 ? "rgba(74, 222, 128, 0.2)" :
                                                                                   memory.combined_score >= 0.6 ? "rgba(251, 191, 36, 0.2)" : "rgba(248, 113, 113, 0.2)",
                                                                        color: memory.combined_score >= 0.8 ? "#4ade80" :
                                                                               memory.combined_score >= 0.6 ? "#fbbf24" : "#f87171",
                                                                        padding: "0.1rem 0.3rem",
                                                                        borderRadius: "3px",
                                                                        fontSize: "0.6rem",
                                                                        fontWeight: 600
                                                                    }}>
                                                                        Score: {memory.combined_score.toFixed(2)}
                                                                    </span>
                                                                    {/* Importance Badge */}
                                                                    <span style={{
                                                                        background: memory.importance >= 0.8 ? "rgba(74, 222, 128, 0.2)" :
                                                                                   memory.importance >= 0.6 ? "rgba(251, 191, 36, 0.2)" : "rgba(248, 113, 113, 0.2)",
                                                                        color: memory.importance >= 0.8 ? "#4ade80" :
                                                                               memory.importance >= 0.6 ? "#fbbf24" : "#f87171",
                                                                        padding: "0.1rem 0.3rem",
                                                                        borderRadius: "3px",
                                                                        fontSize: "0.6rem",
                                                                        fontWeight: 600
                                                                    }}>
                                                                        Imp: {memory.importance.toFixed(2)}
                                                                    </span>
                                                                    {/* Confidence Badge */}
                                                                    <span style={{
                                                                        background: memory.confidence === "high" ? "rgba(34, 197, 94, 0.2)" :
                                                                                   memory.confidence === "medium" ? "rgba(251, 191, 36, 0.2)" : "rgba(248, 113, 113, 0.2)",
                                                                        color: memory.confidence === "high" ? "#22c55e" :
                                                                               memory.confidence === "medium" ? "#fbbf24" : "#f87171",
                                                                        padding: "0.1rem 0.3rem",
                                                                        borderRadius: "3px",
                                                                        fontSize: "0.6rem",
                                                                        fontWeight: 600
                                                                    }}>
                                                                        {memory.confidence}
                                                                    </span>
                                                                </div>
                                                            </div>
                                                            <div style={{ 
                                                                display: "flex", 
                                                                gap: "0.5rem", 
                                                                color: "var(--muted)",
                                                                fontSize: "0.6rem"
                                                            }}>
                                                                <span>Similarity: {memory.similarity_score.toFixed(2)}</span>
                                                                <span>Recency: {memory.recency_score.toFixed(2)}</span>
                                                                <span>Access: {memory.access_count}x</span>
                                                                <span>Age: {memory.age_days.toFixed(1)}d</span>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                        
                                        <div style={{ 
                                            fontSize: "0.8rem", 
                                            fontWeight: 600, 
                                            color: "var(--muted)",
                                            marginBottom: "0.5rem",
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "0.5rem"
                                        }}>
                                            🛠️ Tools Used ({msg.tools_used})
                                            {msg.reasoning_steps && msg.reasoning_steps.length > 0 && (
                                                <span style={{ 
                                                    fontSize: "0.7rem", 
                                                    color: "#8b5cf6",
                                                    background: "rgba(139, 92, 246, 0.1)",
                                                    padding: "0.1rem 0.4rem",
                                                    borderRadius: "4px"
                                                }}>
                                                    {msg.reasoning_steps.length} Steps
                                                </span>
                                            )}
                                        </div>
                                        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                                            {msg.tool_calls.map((toolCall, idx) => (
                                                <div
                                                    key={idx}
                                                    style={{
                                                        background: "rgba(34, 197, 94, 0.1)",
                                                        border: "1px solid rgba(34, 197, 94, 0.2)",
                                                        borderRadius: "var(--radius-sm)",
                                                        padding: "0.5rem 0.75rem",
                                                        fontSize: "0.8rem",
                                                    }}
                                                >
                                                    <div style={{ 
                                                        display: "flex", 
                                                        alignItems: "center", 
                                                        gap: "0.5rem",
                                                        marginBottom: "0.25rem",
                                                        flexWrap: "wrap"
                                                    }}>
                                                        <span style={{ 
                                                            fontWeight: 600, 
                                                            color: "#22c55e" 
                                                        }}>
                                                            {toolCall.tool_name}
                                                        </span>
                                                        <span style={{ 
                                                            fontSize: "0.7rem", 
                                                            color: "var(--muted)",
                                                            background: "rgba(34, 197, 94, 0.1)",
                                                            padding: "0.1rem 0.4rem",
                                                            borderRadius: "4px"
                                                        }}>
                                                            {toolCall.result.success ? "✅ Success" : "❌ Failed"}
                                                        </span>
                                                    </div>
                                                    {Object.keys(toolCall.arguments).length > 0 && (
                                                        <div style={{ 
                                                            fontSize: "0.7rem", 
                                                            color: "var(--muted)",
                                                            marginBottom: "0.25rem"
                                                        }}>
                                                            Args: {JSON.stringify(toolCall.arguments)}
                                                        </div>
                                                    )}
                                                    <div style={{ 
                                                        color: "var(--muted)", 
                                                        lineHeight: 1.4,
                                                        fontSize: "0.75rem"
                                                    }}>
                                                        {toolCall.result.success 
                                                            ? (toolCall.result.message || toolCall.result.answer || "Tool executed successfully")
                                                            : (toolCall.result.error || "Tool execution failed")
                                                        }
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                
                                {/* Sources section */}
                                {msg.sources && msg.sources.length > 0 && !msg.streaming && (
                                    <div style={{ 
                                        marginTop: "1rem", 
                                        paddingTop: "1rem", 
                                        borderTop: "1px solid var(--border)",
                                    }}>
                                        <div style={{ 
                                            fontSize: "0.8rem", 
                                            fontWeight: 600, 
                                            color: "var(--muted)",
                                            marginBottom: "0.5rem",
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "0.5rem"
                                        }}>
                                            📚 Sources
                                        </div>
                                        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                                            {msg.sources.map((source, idx) => (
                                                <div
                                                    key={idx}
                                                    style={{
                                                        background: "rgba(0,0,0,0.2)",
                                                        border: "1px solid var(--border)",
                                                        borderRadius: "var(--radius-sm)",
                                                        padding: "0.5rem 0.75rem",
                                                        fontSize: "0.8rem",
                                                    }}
                                                >
                                                    <div style={{ 
                                                        display: "flex", 
                                                        alignItems: "center", 
                                                        gap: "0.5rem",
                                                        marginBottom: "0.25rem",
                                                        flexWrap: "wrap"
                                                    }}>
                                                        <span style={{ 
                                                            fontWeight: 600, 
                                                            color: "var(--accent2)" 
                                                        }}>
                                                            {source.doc}
                                                        </span>
                                                        <span style={{ 
                                                            fontSize: "0.7rem", 
                                                            color: "var(--muted)",
                                                            background: "rgba(225, 29, 72, 0.1)",
                                                            padding: "0.1rem 0.4rem",
                                                            borderRadius: "4px"
                                                        }}>
                                                            Page {source.page}
                                                        </span>
                                                        {source.doc_coverage && (
                                                            <span style={{ 
                                                                fontSize: "0.65rem", 
                                                                color: "#f59e0b",
                                                                background: "rgba(245, 158, 11, 0.1)",
                                                                padding: "0.1rem 0.3rem",
                                                                borderRadius: "3px"
                                                            }}>
                                                                {source.doc_coverage}% coverage
                                                            </span>
                                                        )}
                                                        {source.search_types && (
                                                            <div style={{ display: "flex", gap: "0.25rem" }}>
                                                                {source.search_types.includes("vector") && (
                                                                    <span style={{ 
                                                                        fontSize: "0.65rem", 
                                                                        color: "#3b82f6",
                                                                        background: "rgba(59, 130, 246, 0.1)",
                                                                        padding: "0.1rem 0.3rem",
                                                                        borderRadius: "3px"
                                                                    }}>
                                                                        Vector
                                                                    </span>
                                                                )}
                                                                {source.search_types.includes("keyword") && (
                                                                    <span style={{ 
                                                                        fontSize: "0.65rem", 
                                                                        color: "#8b5cf6",
                                                                        background: "rgba(139, 92, 246, 0.1)",
                                                                        padding: "0.1rem 0.3rem",
                                                                        borderRadius: "3px"
                                                                    }}>
                                                                        Keyword
                                                                    </span>
                                                                )}
                                                            </div>
                                                        )}
                                                        {source.hybrid_score && (
                                                            <span style={{ 
                                                                fontSize: "0.65rem", 
                                                                color: "#22c55e",
                                                                background: "rgba(34, 197, 94, 0.1)",
                                                                padding: "0.1rem 0.3rem",
                                                                borderRadius: "3px",
                                                                fontWeight: 600
                                                            }}>
                                                                Score: {source.hybrid_score}
                                                            </span>
                                                        )}
                                                        {source.combined_score && (
                                                            <span style={{ 
                                                                fontSize: "0.65rem", 
                                                                color: "#22c55e",
                                                                background: "rgba(34, 197, 94, 0.1)",
                                                                padding: "0.1rem 0.3rem",
                                                                borderRadius: "3px",
                                                                fontWeight: 600
                                                            }}>
                                                                Final: {source.combined_score}
                                                            </span>
                                                        )}
                                                        {source.compressed && (
                                                            <span style={{ 
                                                                fontSize: "0.65rem", 
                                                                color: "#f59e0b",
                                                                background: "rgba(245, 158, 11, 0.1)",
                                                                padding: "0.1rem 0.3rem",
                                                                borderRadius: "3px"
                                                            }}>
                                                                Compressed
                                                            </span>
                                                        )}
                                                    </div>
                                                    {source.matched_terms && source.matched_terms.length > 0 && (
                                                        <div style={{ 
                                                            fontSize: "0.65rem", 
                                                            color: "#8b5cf6",
                                                            marginBottom: "0.25rem"
                                                        }}>
                                                            Keywords: {source.matched_terms.join(", ")}
                                                        </div>
                                                    )}
                                                    <div style={{ 
                                                        color: "var(--muted)", 
                                                        lineHeight: 1.4,
                                                        fontSize: "0.75rem"
                                                    }}>
                                                        {source.text}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Metadata section */}
                                {msg.metadata && !msg.streaming && (
                                    <div style={{ 
                                        marginTop: "1rem", 
                                        paddingTop: "1rem", 
                                        borderTop: "1px solid var(--border)",
                                    }}>
                                        <div style={{ 
                                            fontSize: "0.8rem", 
                                            fontWeight: 600, 
                                            color: "var(--muted)",
                                            marginBottom: "0.5rem",
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "0.5rem"
                                        }}>
                                            📊 Usage Metrics
                                            {msg.metadata.pipeline_version === "multi_doc_hybrid_v1" && (
                                                <span style={{
                                                    fontSize: "0.65rem",
                                                    background: "rgba(34, 197, 94, 0.1)",
                                                    color: "#22c55e",
                                                    padding: "0.1rem 0.4rem",
                                                    borderRadius: "4px",
                                                    fontWeight: 600
                                                }}>
                                                    Multi-Document
                                                </span>
                                            )}
                                            {msg.metadata.pipeline_version === "hybrid_v1" && (
                                                <span style={{
                                                    fontSize: "0.65rem",
                                                    background: "rgba(139, 92, 246, 0.1)",
                                                    color: "#8b5cf6",
                                                    padding: "0.1rem 0.4rem",
                                                    borderRadius: "4px",
                                                    fontWeight: 600
                                                }}>
                                                    Hybrid Search
                                                </span>
                                            )}
                                        </div>
                                        
                                        {/* Multi-Document Analysis */}
                                        {msg.metadata.document_analysis && msg.metadata.document_analysis.multi_document && (
                                            <div style={{ 
                                                display: "grid", 
                                                gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))", 
                                                gap: "0.5rem",
                                                fontSize: "0.7rem",
                                                marginBottom: "0.75rem",
                                                padding: "0.5rem",
                                                background: "rgba(34, 197, 94, 0.05)",
                                                borderRadius: "var(--radius-sm)",
                                                border: "1px solid rgba(34, 197, 94, 0.1)"
                                            }}>
                                                <div style={{
                                                    textAlign: "center"
                                                }}>
                                                    <div style={{ color: "#22c55e", fontWeight: 600 }}>
                                                        {msg.metadata.document_analysis.document_count}
                                                    </div>
                                                    <div style={{ color: "var(--muted)", fontSize: "0.65rem" }}>Documents</div>
                                                </div>
                                                <div style={{
                                                    textAlign: "center"
                                                }}>
                                                    <div style={{ color: "#22c55e", fontWeight: 600 }}>
                                                        {msg.metadata.context_metadata?.context_length || 0}
                                                    </div>
                                                    <div style={{ color: "var(--muted)", fontSize: "0.65rem" }}>Context Chars</div>
                                                </div>
                                                <div style={{
                                                    textAlign: "center"
                                                }}>
                                                    <div style={{ color: "#22c55e", fontWeight: 600 }}>
                                                        Cross-Doc
                                                    </div>
                                                    <div style={{ color: "var(--muted)", fontSize: "0.65rem" }}>Analysis</div>
                                                </div>
                                            </div>
                                        )}
                                        
                                        {/* Hybrid Search Stats */}
                                        {msg.metadata.hybrid_stats && (
                                            <div style={{ 
                                                display: "grid", 
                                                gridTemplateColumns: "repeat(auto-fit, minmax(80px, 1fr))", 
                                                gap: "0.5rem",
                                                fontSize: "0.7rem",
                                                marginBottom: "0.75rem"
                                            }}>
                                                <div style={{
                                                    background: "rgba(59, 130, 246, 0.1)",
                                                    border: "1px solid rgba(59, 130, 246, 0.2)",
                                                    borderRadius: "var(--radius-sm)",
                                                    padding: "0.3rem 0.5rem",
                                                    textAlign: "center"
                                                }}>
                                                    <div style={{ color: "#3b82f6", fontWeight: 600 }}>
                                                        {msg.metadata.hybrid_stats.vector_only || 0}
                                                    </div>
                                                    <div style={{ color: "var(--muted)", fontSize: "0.65rem" }}>Vector Only</div>
                                                </div>
                                                <div style={{
                                                    background: "rgba(139, 92, 246, 0.1)",
                                                    border: "1px solid rgba(139, 92, 246, 0.2)",
                                                    borderRadius: "var(--radius-sm)",
                                                    padding: "0.3rem 0.5rem",
                                                    textAlign: "center"
                                                }}>
                                                    <div style={{ color: "#8b5cf6", fontWeight: 600 }}>
                                                        {msg.metadata.hybrid_stats.keyword_only || 0}
                                                    </div>
                                                    <div style={{ color: "var(--muted)", fontSize: "0.65rem" }}>Keyword Only</div>
                                                </div>
                                                <div style={{
                                                    background: "rgba(34, 197, 94, 0.1)",
                                                    border: "1px solid rgba(34, 197, 94, 0.2)",
                                                    borderRadius: "var(--radius-sm)",
                                                    padding: "0.3rem 0.5rem",
                                                    textAlign: "center"
                                                }}>
                                                    <div style={{ color: "#22c55e", fontWeight: 600 }}>
                                                        {msg.metadata.hybrid_stats.both_methods || 0}
                                                    </div>
                                                    <div style={{ color: "var(--muted)", fontSize: "0.65rem" }}>Both Methods</div>
                                                </div>
                                            </div>
                                        )}
                                        <div style={{ 
                                            display: "grid", 
                                            gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))", 
                                            gap: "0.5rem",
                                            fontSize: "0.75rem"
                                        }}>
                                            <div style={{
                                                background: "rgba(0,0,0,0.2)",
                                                border: "1px solid var(--border)",
                                                borderRadius: "var(--radius-sm)",
                                                padding: "0.4rem 0.6rem",
                                                textAlign: "center"
                                            }}>
                                                <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                                    {msg.metadata.chunks_found}
                                                </div>
                                                <div style={{ color: "var(--muted)" }}>Found</div>
                                            </div>
                                            {msg.metadata.final_chunks && (
                                                <div style={{
                                                    background: "rgba(0,0,0,0.2)",
                                                    border: "1px solid var(--border)",
                                                    borderRadius: "var(--radius-sm)",
                                                    padding: "0.4rem 0.6rem",
                                                    textAlign: "center"
                                                }}>
                                                    <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                                        {msg.metadata.final_chunks}
                                                    </div>
                                                    <div style={{ color: "var(--muted)" }}>Used</div>
                                                </div>
                                            )}
                                            <div style={{
                                                background: "rgba(0,0,0,0.2)",
                                                border: "1px solid var(--border)",
                                                borderRadius: "var(--radius-sm)",
                                                padding: "0.4rem 0.6rem",
                                                textAlign: "center"
                                            }}>
                                                <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                                    {msg.metadata.prompt_tokens.toLocaleString()}
                                                </div>
                                                <div style={{ color: "var(--muted)" }}>Prompt</div>
                                            </div>
                                            <div style={{
                                                background: "rgba(0,0,0,0.2)",
                                                border: "1px solid var(--border)",
                                                borderRadius: "var(--radius-sm)",
                                                padding: "0.4rem 0.6rem",
                                                textAlign: "center"
                                            }}>
                                                <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                                    {msg.metadata.completion_tokens.toLocaleString()}
                                                </div>
                                                <div style={{ color: "var(--muted)" }}>Response</div>
                                            </div>
                                            <div style={{
                                                background: "rgba(0,0,0,0.2)",
                                                border: "1px solid var(--border)",
                                                borderRadius: "var(--radius-sm)",
                                                padding: "0.4rem 0.6rem",
                                                textAlign: "center"
                                            }}>
                                                <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                                    {msg.metadata.total_tokens.toLocaleString()}
                                                </div>
                                                <div style={{ color: "var(--muted)" }}>Total</div>
                                            </div>
                                            <div style={{
                                                background: "rgba(0,0,0,0.2)",
                                                border: "1px solid var(--border)",
                                                borderRadius: "var(--radius-sm)",
                                                padding: "0.4rem 0.6rem",
                                                textAlign: "center"
                                            }}>
                                                <div style={{ color: "var(--accent2)", fontWeight: 600 }}>
                                                    {msg.metadata.latency}ms
                                                </div>
                                                <div style={{ color: "var(--muted)" }}>Latency</div>
                                            </div>
                                            {msg.metadata.pipeline_version && (
                                                <div style={{
                                                    background: msg.metadata.pipeline_version === "multi_doc_hybrid_v1" 
                                                        ? "rgba(34, 197, 94, 0.1)" 
                                                        : msg.metadata.pipeline_version === "hybrid_v1"
                                                        ? "rgba(139, 92, 246, 0.1)" 
                                                        : "rgba(34, 197, 94, 0.1)",
                                                    border: msg.metadata.pipeline_version === "multi_doc_hybrid_v1"
                                                        ? "1px solid rgba(34, 197, 94, 0.3)"
                                                        : msg.metadata.pipeline_version === "hybrid_v1"
                                                        ? "1px solid rgba(139, 92, 246, 0.3)"
                                                        : "1px solid rgba(34, 197, 94, 0.3)",
                                                    borderRadius: "var(--radius-sm)",
                                                    padding: "0.4rem 0.6rem",
                                                    textAlign: "center"
                                                }}>
                                                    <div style={{ 
                                                        color: msg.metadata.pipeline_version === "multi_doc_hybrid_v1" 
                                                            ? "#22c55e" 
                                                            : msg.metadata.pipeline_version === "hybrid_v1" 
                                                            ? "#8b5cf6" 
                                                            : "#22c55e", 
                                                        fontWeight: 600, 
                                                        fontSize: "0.7rem" 
                                                    }}>
                                                        {msg.metadata.pipeline_version === "multi_doc_hybrid_v1" 
                                                            ? "Multi-Doc" 
                                                            : msg.metadata.pipeline_version === "hybrid_v1" 
                                                            ? "Hybrid" 
                                                            : "Enhanced"}
                                                    </div>
                                                    <div style={{ color: "var(--muted)" }}>Pipeline</div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>

            {/* Input bar */}
            <div className="glass" style={{
                display: "flex",
                alignItems: "flex-end",
                gap: "1rem",
                padding: "1rem 1.25rem",
                borderRadius: "var(--radius-lg)",
                position: "sticky",
                bottom: "1rem",
            }}>
                {processingDoc ? (
                    <div style={{ 
                        flex: 1, 
                        display: "flex", 
                        alignItems: "center", 
                        gap: "1rem",
                        color: "var(--muted)",
                        fontSize: "0.95rem"
                    }}>
                        <div style={{
                            width: 20,
                            height: 20,
                            border: "2px solid var(--border)",
                            borderTop: "2px solid #f59e0b",
                            borderRadius: "50%",
                            animation: "spin 1s linear infinite",
                        }} />
                        <span>{processingStatus || "Processing document..."}</span>
                    </div>
                ) : (
                    <>
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                    e.preventDefault();
                                    sendMessage();
                                }
                            }}
                            placeholder={agentMode 
                                ? "Ask me anything! I can search documents, calculate, get weather info..."
                                : "Ask questions about your PDF document..."
                            }
                            disabled={loading || processingDoc}
                            rows={1}
                            style={{
                                flex: 1,
                                background: "transparent",
                                border: "none",
                                outline: "none",
                                color: "var(--fg)",
                                fontSize: "0.95rem",
                                resize: "none",
                                lineHeight: 1.6,
                                maxHeight: "120px",
                                overflowY: "auto",
                            }}
                        />
                        <button
                            className="accent-btn"
                            onClick={sendMessage}
                            disabled={loading || !input.trim() || processingDoc}
                            style={{ 
                                flexShrink: 0, 
                                padding: "0.75rem 1.5rem", 
                                fontSize: "0.9rem",
                                fontWeight: 600
                            }}
                        >
                            {loading ? "..." : "Send"}
                        </button>
                    </>
                )}
            </div>

            {/* Animations */}
            <style>{`
                @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
                @keyframes spin { 0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)} }
            `}</style>
        </div>
    );
}