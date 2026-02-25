"use client";

type Mode = "normal" | "stream" | "structured";

interface ModeSelectorProps {
    onSelect: (mode: Mode) => void;
}

const modes: {
    id: Mode;
    icon: string;
    title: string;
    description: string;
    tag: string;
    tagColor: string;
}[] = [
        {
            id: "normal",
            icon: "💬",
            title: "Normal Chat",
            description:
                "The AI thinks, then replies all at once. Great for concise, polished answers.",
            tag: "Synchronous",
            tagColor: "#4ade80",
        },
        {
            id: "stream",
            icon: "⚡",
            title: "Streamed Chat",
            description:
                "Words appear in real time as the AI generates them — feels fast and alive.",
            tag: "Real-time",
            tagColor: "#facc15",
        },
        {
            id: "structured",
            icon: "🧠",
            title: "Structured Stream",
            description:
                "Streams the response live, but always replies in JSON with a summary and confidence score.",
            tag: "JSON output",
            tagColor: "#818cf8",
        },
    ];

export default function ModeSelector({ onSelect }: ModeSelectorProps) {
    return (
        <div
            style={{
                minHeight: "100vh",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "2rem",
                gap: "2.5rem",
            }}
        >
            {/* Header */}
            <div style={{ textAlign: "center" }}>
                <h1
                    className="gradient-text"
                    style={{ fontSize: "2.5rem", fontWeight: 800, letterSpacing: "-0.03em" }}
                >
                    AI Chat Studio
                </h1>
                <p style={{ marginTop: "0.75rem", color: "var(--muted)", fontSize: "1.05rem" }}>
                    Choose how you'd like the AI to respond before you start chatting.
                </p>
            </div>

            {/* Cards */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(270px, 1fr))",
                    gap: "1.25rem",
                    width: "100%",
                    maxWidth: "900px",
                }}
            >
                {modes.map((m) => (
                    <button
                        key={m.id}
                        onClick={() => onSelect(m.id)}
                        className="glass"
                        style={{
                            borderRadius: "var(--radius-lg)",
                            padding: "2rem 1.75rem",
                            textAlign: "left",
                            cursor: "pointer",
                            transition: "transform 0.18s, box-shadow 0.18s, border-color 0.18s",
                            display: "flex",
                            flexDirection: "column",
                            gap: "1rem",
                            color: "var(--fg)",
                            background: "var(--glass)",
                        }}
                        onMouseEnter={(e) => {
                            (e.currentTarget as HTMLElement).style.transform = "translateY(-4px)";
                            (e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow)";
                            (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.18)";
                        }}
                        onMouseLeave={(e) => {
                            (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
                            (e.currentTarget as HTMLElement).style.boxShadow = "none";
                            (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                        }}
                    >
                        <div style={{ fontSize: "2.25rem" }}>{m.icon}</div>

                        <div>
                            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.4rem" }}>
                                <span style={{ fontSize: "1.2rem", fontWeight: 700 }}>{m.title}</span>
                                <span
                                    style={{
                                        fontSize: "0.7rem",
                                        fontWeight: 600,
                                        padding: "0.2rem 0.6rem",
                                        borderRadius: "9999px",
                                        background: `${m.tagColor}22`,
                                        color: m.tagColor,
                                        border: `1px solid ${m.tagColor}44`,
                                        textTransform: "uppercase",
                                        letterSpacing: "0.06em",
                                    }}
                                >
                                    {m.tag}
                                </span>
                            </div>
                            <p style={{ color: "var(--muted)", fontSize: "0.9rem", lineHeight: 1.6 }}>
                                {m.description}
                            </p>
                        </div>

                        <div
                            className="gradient-text"
                            style={{ fontSize: "0.875rem", fontWeight: 600, marginTop: "auto" }}
                        >
                            Start chatting →
                        </div>
                    </button>
                ))}
            </div>
        </div>
    );
}
