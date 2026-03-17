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
        cosine_similarity?: number;
        compressed?: boolean;
        original_length?: number;
        search_types?: string[];
        hybrid_score?: number;
        vector_score?: number;
        keyword_score?: number;
        matched_terms?: string[];
        doc_coverage?: number;
        doc_avg_score?: number;
    }>;
    metadata?: {
        chunks_found: number;
        initial_chunks?: number;
        reranked_chunks?: number;
        final_chunks?: number;
        hybrid_stats?: {
            total: number;
            vector_only?: number;
            keyword_only?: number;
            both_methods?: number;
            avg_hybrid_score?: number;
            top_score?: number;
        };
        document_analysis?: {
            document_count: number;
            multi_document: boolean;
            total_chunks: number;
            document_stats?: Record<string, {
                chunk_count: number;
                coverage_percentage: number;
                page_range: string;
                avg_hybrid_score: number;
                search_types: string[];
            }>;
        };
        context_metadata?: {
            documents: number;
            total_chunks: number;
            context_length: number;
            multi_document_analysis: boolean;
            included_documents?: Record<string, any>;
        };
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
    reasoning_steps?: Array<{
        step: number;
        tools_used: Array<{
            tool_name: string;
            arguments: any;
            result: any;
        }>;
        reasoning: string;
    }>;
    react_pattern?: boolean;
    memory_used?: boolean;
}

export default function PDFRagPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [documentUploaded, setDocumentUploaded] = useState(false);
    const [uploadingDoc, setUploadingDoc] = useState(false);
    const [processingDoc, setProcessingDoc] = useState(false);
    const [processingStatus, setProcessingStatus] = useState("");
    const [persistenceStatus, setPersistenceStatus] = useState<any>(null);
    const [showPersistencePanel, setShowPersistencePanel] = useState(false);
    const [memoryStatus, setMemoryStatus] = useState<any>(null);
    const [agentMode, setAgentMode] = useState(false); // New state for agent mode
    const bottomRef = useRef<HTMLDivElement>(null);
    const router = useRouter();

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Load persistence status on component mount
    useEffect(() => {
        checkPersistenceStatus();
    }, []);

    const checkPersistenceStatus = async () => {
        try {
            const res = await fetch('http://localhost:8000/persistence/status');
            if (res.ok) {
                const data = await res.json();
                setPersistenceStatus(data);
            }
        } catch (error) {
            console.error('Persistence status check error:', error);
        }
    };

    const checkMemoryStatus = async () => {
        try {
            const res = await fetch('http://localhost:8000/memory/status');
            if (res.ok) {
                const data = await res.json();
                setMemoryStatus(data.memory_stats);
            }
        } catch (error) {
            console.error('Memory status check error:', error);
        }
    };

    const clearChatMemory = async () => {
        try {
            const res = await fetch('http://localhost:8000/memory/clear-chat', {
                method: 'POST'
            });
            if (res.ok) {
                const data = await res.json();
                setMessages([{ 
                    role: "ai", 
                    content: `✅ ${data.message}\n\nChat history has been cleared. The agent will start fresh without previous conversation context.` 
                }]);
                // Refresh memory status
                setTimeout(checkMemoryStatus, 1000);
            }
        } catch (error) {
            console.error('Clear chat memory error:', error);
            setMessages([{ 
                role: "ai", 
                content: "❌ Error clearing chat memory. Please check if the backend is running." 
            }]);
        }
    };

    const clearAllMemory = async () => {
        if (!confirm('⚠️ This will permanently delete ALL agent memory (chat history + stored facts). Are you sure?')) {
            return;
        }
        
        try {
            const res = await fetch('http://localhost:8000/memory/clear-all', {
                method: 'POST'
            });
            if (res.ok) {
                const data = await res.json();
                setMessages([{ 
                    role: "ai", 
                    content: `✅ ${data.message}\n\nAll agent memory has been permanently cleared. The agent will start completely fresh.` 
                }]);
                // Refresh memory status
                setTimeout(checkMemoryStatus, 1000);
            }
        } catch (error) {
            console.error('Clear all memory error:', error);
            setMessages([{ 
                role: "ai", 
                content: "❌ Error clearing all memory. Please check if the backend is running." 
            }]);
        }
    };

    const cleanupOldMemories = async () => {
        try {
            const res = await fetch('http://localhost:8000/memory/cleanup', {
                method: 'POST'
            });
            if (res.ok) {
                const data = await res.json();
                setMessages([{ 
                    role: "ai", 
                    content: `✅ ${data.message}\n\nOld memories have been cleaned up and decay has been applied to aging memories.` 
                }]);
                // Refresh memory status
                setTimeout(checkMemoryStatus, 1000);
            }
        } catch (error) {
            console.error('Memory cleanup error:', error);
            setMessages([{ 
                role: "ai", 
                content: "❌ Error cleaning up memories. Please check if the backend is running." 
            }]);
        }
    };

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
                // Refresh persistence status
                setTimeout(checkPersistenceStatus, 1000);
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
            console.log('Sending question:', text, 'Agent mode:', agentMode);
            
            // Choose endpoint based on mode
            const endpoint = agentMode ? 'agent-stream' : 'ask-stream';
            const res = await fetch(`http://localhost:8000/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: agentMode ? `query=${encodeURIComponent(text)}` : `question=${encodeURIComponent(text)}`,
            });
            
            console.log('Response status:', res.status);
            
            if (!res.ok) {
                const errorText = await res.text();
                console.error('Response error:', errorText);
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
                buffer = events.pop() || ''; // Keep incomplete event in buffer
                
                for (const event of events) {
                    if (event.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(event.slice(6));
                            if (data.done) {
                                // Mark streaming as complete
                                setMessages((prev) => {
                                    const updated = [...prev];
                                    const last = { ...updated[updated.length - 1] };
                                    last.streaming = false;
                                    updated[updated.length - 1] = last;
                                    return updated;
                                });
                            } else if (agentMode) {
                                // Handle agent streaming response
                                if (data.type === "metadata") {
                                    setMessages((prev) => {
                                        const updated = [...prev];
                                        const last = { ...updated[updated.length - 1] };
                                        last.tools_used = data.tools_used;
                                        last.tool_calls = data.tool_calls;
                                        last.has_tool_calls = data.has_tool_calls;
                                        last.reasoning_steps = data.reasoning_steps;
                                        last.react_pattern = data.react_pattern;
                                        last.memory_used = data.memory_used;
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
                                // Handle regular RAG streaming response
                                if (data.answer !== undefined) {
                                    // Append answer chunk and update sources/metadata
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
                        }]);
                    } else {
                        setMessages([{ 
                            role: "ai", 
                            content: `✅ PDF processed successfully!\n\nYour document is now ready for questions. You can ask anything about the content.` 
                        }]);
                    }
                    return true; // Processing complete
                } else {
                    setProcessingStatus(`Processing document... (${data.documents_loaded} chunks loaded)`);
                    return false; // Still processing
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
            
            console.log('Upload response status:', res.status);
            
            if (res.ok) {
                const data = await res.json();
                console.log('Upload response data:', data);
                
                // Start processing status polling
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
                        setMessages([{ 
                            role: "ai", 
                            content: `✅ PDF processed successfully!\n\nYour document is now ready for questions. You can ask anything about the content.` 
                        }]);
                        // Refresh persistence status after successful processing
                        checkPersistenceStatus();
                    }
                }, 2000); // Check every 2 seconds
                
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
                console.error('Upload error:', errorText);
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
                        onClick={() => router.push("/")}
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
                        <span style={{ fontSize: "1.3rem" }}>📚</span>
                        <span style={{ fontWeight: 700, fontSize: "1rem" }}>PDF RAG Assistant</span>
                        <span
                            style={{
                                fontSize: "0.68rem",
                                padding: "0.15rem 0.55rem",
                                borderRadius: "9999px",
                                background: "#e11d4822",
                                color: "#e11d48",
                                border: "1px solid #e11d4844",
                                textTransform: "uppercase",
                                letterSpacing: "0.06em",
                                fontWeight: 600,
                            }}
                        >
                            PDF Chat
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
                            📚 Upload Your PDF Documents
                        </h2>
                        <p style={{ color: "var(--muted)", marginBottom: "1.5rem", lineHeight: 1.6 }}>
                            Upload PDF files to start chatting with them. You can upload multiple documents for cross-document 
                            analysis and comparison. The documents will be processed using advanced RAG (Retrieval-Augmented Generation) 
                            techniques with FAISS vector search and OpenAI embeddings.
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
                                    (e.currentTarget as HTMLElement).style.borderColor = "#e11d48";
                                    (e.currentTarget as HTMLElement).style.background = "#e11d4811";
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
                                    if (file && file.type === 'application/pdf') {
                                        handleFileUpload(file);
                                    }
                                }}
                            >
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
                                <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>📄</div>
                                <div style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.25rem" }}>
                                    {uploadingDoc ? "Processing PDF..." : "Click to browse or drag & drop"}
                                </div>
                                <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                                    Supports PDF files only
                                </div>
                            </label>
                        </div>

                        {/* Features */}
                        <div style={{ 
                            display: "grid", 
                            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", 
                            gap: "1rem",
                            marginTop: "2rem"
                        }}>
                            <div style={{ 
                                padding: "1rem", 
                                background: "rgba(0,0,0,0.2)", 
                                borderRadius: "var(--radius-md)",
                                textAlign: "center"
                            }}>
                                <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>🔍</div>
                                <div style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.25rem" }}>Smart Search</div>
                                <div style={{ fontSize: "0.8rem", color: "var(--muted)" }}>FAISS vector similarity search</div>
                            </div>
                            <div style={{ 
                                padding: "1rem", 
                                background: "rgba(0,0,0,0.2)", 
                                borderRadius: "var(--radius-md)",
                                textAlign: "center"
                            }}>
                                <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>🧠</div>
                                <div style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.25rem" }}>AI Powered</div>
                                <div style={{ fontSize: "0.8rem", color: "var(--muted)" }}>OpenAI GPT-4 responses</div>
                            </div>
                            <div style={{ 
                                padding: "1rem", 
                                background: "rgba(0,0,0,0.2)", 
                                borderRadius: "var(--radius-md)",
                                textAlign: "center"
                            }}>
                                <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>⚡</div>
                                <div style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.25rem" }}>Fast Processing</div>
                                <div style={{ fontSize: "0.8rem", color: "var(--muted)" }}>Chunked text embeddings</div>
                            </div>
                        </div>
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
                    flexWrap: "wrap",
                }}
            >
                <button
                    onClick={() => router.push("/")}
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
                    <span style={{ fontSize: "1.3rem" }}>📚</span>
                    <span style={{ fontWeight: 700, fontSize: "1rem" }}>PDF RAG Assistant</span>
                    <span
                        style={{
                            fontSize: "0.68rem",
                            padding: "0.15rem 0.55rem",
                            borderRadius: "9999px",
                            background: agentMode ? "#22c55e22" : "#e11d4822",
                            color: agentMode ? "#22c55e" : "#e11d48",
                            border: agentMode ? "1px solid #22c55e44" : "1px solid #e11d4844",
                            textTransform: "uppercase",
                            letterSpacing: "0.06em",
                            fontWeight: 600,
                        }}
                    >
                        {agentMode ? "AI Agent" : "PDF Chat"}
                    </span>
                </div>

                {/* Mode Toggle - Made more prominent */}
                <div style={{ 
                    display: "flex", 
                    alignItems: "center", 
                    gap: "0.5rem",
                    background: "rgba(0,0,0,0.1)",
                    padding: "0.25rem",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border)"
                }}>
                    <span style={{ 
                        fontSize: "0.7rem", 
                        color: "var(--muted)", 
                        fontWeight: 600,
                        paddingLeft: "0.5rem"
                    }}>
                        MODE:
                    </span>
                    <button
                        onClick={() => setAgentMode(!agentMode)}
                        style={{
                            background: agentMode ? "rgba(34, 197, 94, 0.15)" : "rgba(225, 29, 72, 0.15)",
                            border: agentMode ? "2px solid rgba(34, 197, 94, 0.4)" : "2px solid rgba(225, 29, 72, 0.4)",
                            color: agentMode ? "#22c55e" : "#e11d48",
                            cursor: "pointer",
                            fontSize: "0.85rem",
                            padding: "0.5rem 1rem",
                            borderRadius: "var(--radius-md)",
                            transition: "all 0.15s",
                            fontWeight: 700,
                            minWidth: "120px",
                            textAlign: "center",
                        }}
                        onMouseEnter={(e) => {
                            if (agentMode) {
                                (e.currentTarget as HTMLElement).style.background = "rgba(34, 197, 94, 0.25)";
                                (e.currentTarget as HTMLElement).style.borderColor = "rgba(34, 197, 94, 0.6)";
                            } else {
                                (e.currentTarget as HTMLElement).style.background = "rgba(225, 29, 72, 0.25)";
                                (e.currentTarget as HTMLElement).style.borderColor = "rgba(225, 29, 72, 0.6)";
                            }
                        }}
                        onMouseLeave={(e) => {
                            if (agentMode) {
                                (e.currentTarget as HTMLElement).style.background = "rgba(34, 197, 94, 0.15)";
                                (e.currentTarget as HTMLElement).style.borderColor = "rgba(34, 197, 94, 0.4)";
                            } else {
                                (e.currentTarget as HTMLElement).style.background = "rgba(225, 29, 72, 0.15)";
                                (e.currentTarget as HTMLElement).style.borderColor = "rgba(225, 29, 72, 0.4)";
                            }
                        }}
                    >
                        {agentMode ? "🤖 Agent Mode" : "📄 RAG Mode"}
                    </button>
                </div>

                {/* Status dot */}
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--muted)", fontSize: "0.8rem" }}>
                    <div
                        style={{
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            background: processingDoc ? "#f59e0b" : loading ? "#facc15" : "#4ade80",
                            boxShadow: processingDoc ? "0 0 6px #f59e0b" : loading ? "0 0 6px #facc15" : "0 0 6px #4ade80",
                            transition: "background 0.3s, box-shadow 0.3s",
                        }}
                    />
                    {processingDoc ? "Processing…" : loading ? "Thinking…" : "Ready"}
                </div>

                {/* Add PDF button */}
                <button
                    onClick={() => {
                        setDocumentUploaded(false);
                        setProcessingDoc(false);
                        setProcessingStatus("");
                        // Don't clear messages - preserve chat history for multi-document
                    }}
                    style={{
                        background: "rgba(225, 29, 72, 0.1)",
                        border: "1px solid rgba(225, 29, 72, 0.3)",
                        color: "#e11d48",
                        cursor: "pointer",
                        fontSize: "0.8rem",
                        padding: "0.4rem 0.8rem",
                        borderRadius: "var(--radius-md)",
                        transition: "background 0.15s, border-color 0.15s",
                        fontWeight: 600,
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

                {/* Persistence status button */}
                <button
                    onClick={() => {
                        setShowPersistencePanel(!showPersistencePanel);
                        if (!showPersistencePanel) {
                            checkPersistenceStatus();
                            checkMemoryStatus();
                        }
                    }}
                    style={{
                        background: "rgba(59, 130, 246, 0.1)",
                        border: "1px solid rgba(59, 130, 246, 0.3)",
                        color: "#3b82f6",
                        cursor: "pointer",
                        fontSize: "0.8rem",
                        padding: "0.4rem 0.8rem",
                        borderRadius: "var(--radius-md)",
                        transition: "background 0.15s, border-color 0.15s",
                        fontWeight: 600,
                    }}
                    onMouseEnter={(e) => {
                        (e.currentTarget as HTMLElement).style.background = "rgba(59, 130, 246, 0.15)";
                        (e.currentTarget as HTMLElement).style.borderColor = "rgba(59, 130, 246, 0.4)";
                    }}
                    onMouseLeave={(e) => {
                        (e.currentTarget as HTMLElement).style.background = "rgba(59, 130, 246, 0.1)";
                        (e.currentTarget as HTMLElement).style.borderColor = "rgba(59, 130, 246, 0.3)";
                    }}
                >
                    💾 Cache
                </button>
            </div>

            {/* Persistence Panel */}
            {showPersistencePanel && (
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
                                </div>

                                {/* Memory Distribution */}
                                {memoryStatus.importance_distribution && (
                                    <div style={{ fontSize: "0.75rem" }}>
                                        <div style={{ color: "var(--muted)", marginBottom: "0.25rem" }}>Memory Quality Distribution:</div>
                                        <div style={{ display: "flex", gap: "0.5rem", fontSize: "0.7rem" }}>
                                            <span style={{ color: "#4ade80" }}>
                                                High: {memoryStatus.importance_distribution.high || 0}
                                            </span>
                                            <span style={{ color: "#fbbf24" }}>
                                                Medium: {memoryStatus.importance_distribution.medium || 0}
                                            </span>
                                            <span style={{ color: "#f87171" }}>
                                                Low: {memoryStatus.importance_distribution.low || 0}
                                            </span>
                                        </div>
                                    </div>
                                )}

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
                </div>
            )}

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
                        <span style={{ fontSize: "3rem" }}>{agentMode ? "🤖" : "📚"}</span>
                        <p style={{ fontSize: "1rem", textAlign: "center" }}>
                            {agentMode 
                                ? "AI Agent ready! I can search documents, perform calculations, get weather, and more."
                                : "Your PDF is ready! Ask questions about the document content."
                            }
                        </p>
                        <div style={{ 
                            display: "flex", 
                            flexWrap: "wrap", 
                            gap: "0.5rem", 
                            justifyContent: "center",
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
                                        padding: "0.5rem 1rem",
                                        borderRadius: "var(--radius-md)",
                                        fontSize: "0.85rem",
                                        cursor: "pointer",
                                        transition: "all 0.15s",
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
                                
                                {/* Tool calls section */}
                                {msg.tool_calls && msg.tool_calls.length > 0 && !msg.streaming && (
                                    <div style={{ 
                                        marginTop: "1rem", 
                                        paddingTop: "1rem", 
                                        borderTop: "1px solid var(--border)",
                                    }}>
                                        {/* ReAct Pattern Indicator */}
                                        {msg.react_pattern && (
                                            <div style={{ 
                                                display: "flex",
                                                gap: "0.5rem",
                                                marginBottom: "0.75rem"
                                            }}>
                                                <div style={{ 
                                                    fontSize: "0.75rem", 
                                                    color: "#8b5cf6",
                                                    background: "rgba(139, 92, 246, 0.1)",
                                                    padding: "0.25rem 0.5rem",
                                                    borderRadius: "4px",
                                                    fontWeight: 600
                                                }}>
                                                    🧠 ReAct Pattern: Reason → Act → Observe
                                                </div>
                                                {msg.memory_used && (
                                                    <div style={{ 
                                                        fontSize: "0.75rem", 
                                                        color: "#f59e0b",
                                                        background: "rgba(245, 158, 11, 0.1)",
                                                        padding: "0.25rem 0.5rem",
                                                        borderRadius: "4px",
                                                        fontWeight: 600
                                                    }}>
                                                        💾 Memory Used
                                                    </div>
                                                )}
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
                {processingDoc ? (
                    <div style={{ 
                        flex: 1, 
                        display: "flex", 
                        alignItems: "center", 
                        gap: "0.75rem",
                        color: "var(--muted)",
                        fontSize: "0.9rem"
                    }}>
                        <div
                            style={{
                                width: 16,
                                height: 16,
                                border: "2px solid var(--border)",
                                borderTop: "2px solid #f59e0b",
                                borderRadius: "50%",
                                animation: "spin 1s linear infinite",
                            }}
                        />
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
                                ? "Ask me anything! I can search documents, calculate, get weather, convert currency... (Enter to send, Shift+Enter for newline)"
                                : "Ask questions about your PDF document... (Enter to send, Shift+Enter for newline)"
                            }
                            disabled={loading || processingDoc}
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
                            className="accent-btn"
                            onClick={sendMessage}
                            disabled={loading || !input.trim() || processingDoc}
                            style={{ flexShrink: 0, padding: "0.55rem 1.25rem", fontSize: "0.875rem" }}
                        >
                            {loading ? "…" : "Send"}
                        </button>
                    </>
                )}
            </div>

            {/* Spinning animation */}
            <style>{`
                @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
                @keyframes spin { 0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)} }
            `}</style>
        </div>
    );
}