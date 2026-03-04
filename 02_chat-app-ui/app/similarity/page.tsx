'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface SimilarityResponse {
  similarity_score: number;
  text1: string;
  text2: string;
}

export default function SimilarityChecker() {
  const [text1, setText1] = useState('');
  const [text2, setText2] = useState('');
  const [result, setResult] = useState<SimilarityResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const calculateSimilarity = async () => {
    if (!text1.trim() || !text2.trim()) {
      setError('Please enter both texts');
      return;
    }

    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('http://localhost:8000/api/similarity', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text1: text1.trim(),
          text2: text2.trim(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to calculate similarity');
      }

      const data: SimilarityResponse = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const getSimilarityColor = (score: number) => {
    if (score >= 0.8) return '#4ade80';
    if (score >= 0.6) return '#facc15';
    return '#f87171';
  };

  const getSimilarityLabel = (score: number) => {
    if (score >= 0.8) return 'Very Similar';
    if (score >= 0.6) return 'Moderately Similar';
    if (score >= 0.4) return 'Somewhat Similar';
    return 'Not Similar';
  };

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
          onClick={() => router.push('/')}
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
          <span style={{ fontSize: "1.3rem" }}>📊</span>
          <span style={{ fontWeight: 700, fontSize: "1rem" }}>Cosine Similarity</span>
          <span
            style={{
              fontSize: "0.68rem",
              padding: "0.15rem 0.55rem",
              borderRadius: "9999px",
              background: "#8b5cf622",
              color: "#8b5cf6",
              border: "1px solid #8b5cf644",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              fontWeight: 600,
            }}
          >
            Text Analysis
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
          {loading ? "Calculating…" : "Ready"}
        </div>
      </div>

      {/* Main Content */}
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
        {/* Input Section */}
        <div
          className="glass"
          style={{
            padding: "1.5rem",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <h2 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "1rem", color: "var(--fg)" }}>
            📝 Compare Two Texts
          </h2>
          <p style={{ color: "var(--muted)", marginBottom: "1.5rem", lineHeight: 1.6, fontSize: "0.9rem" }}>
            Enter two texts below to calculate their cosine similarity using OpenAI embeddings. 
            The similarity score ranges from 0 (completely different) to 1 (identical).
          </p>
          
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--fg)" }}>
                Text 1
              </label>
              <textarea
                value={text1}
                onChange={(e) => setText1(e.target.value)}
                placeholder="Enter the first text..."
                disabled={loading}
                style={{
                  width: "100%",
                  minHeight: "120px",
                  padding: "0.875rem",
                  background: "rgba(0,0,0,0.2)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--fg)",
                  fontSize: "0.9rem",
                  fontFamily: "inherit",
                  resize: "vertical",
                  outline: "none",
                  transition: "border-color 0.2s",
                }}
                onFocus={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = "#8b5cf6";
                }}
                onBlur={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                }}
              />
            </div>
            
            <div>
              <label style={{ display: "block", fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--fg)" }}>
                Text 2
              </label>
              <textarea
                value={text2}
                onChange={(e) => setText2(e.target.value)}
                placeholder="Enter the second text..."
                disabled={loading}
                style={{
                  width: "100%",
                  minHeight: "120px",
                  padding: "0.875rem",
                  background: "rgba(0,0,0,0.2)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--fg)",
                  fontSize: "0.9rem",
                  fontFamily: "inherit",
                  resize: "vertical",
                  outline: "none",
                  transition: "border-color 0.2s",
                }}
                onFocus={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = "#8b5cf6";
                }}
                onBlur={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                }}
              />
            </div>
          </div>

          <button
            onClick={calculateSimilarity}
            disabled={loading || !text1.trim() || !text2.trim()}
            className="accent-btn"
            style={{
              width: "100%",
              padding: "0.75rem",
              fontSize: "1rem",
              fontWeight: 600,
            }}
          >
            {loading ? "Calculating Similarity…" : "Calculate Similarity"}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div
            className="glass"
            style={{
              padding: "1rem 1.25rem",
              borderRadius: "var(--radius-lg)",
              border: "1px solid #f8717144",
              background: "#f8717111",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span style={{ fontSize: "1.2rem" }}>⚠️</span>
              <span style={{ color: "#f87171", fontSize: "0.9rem" }}>{error}</span>
            </div>
          </div>
        )}

        {/* Results Display */}
        {result && (
          <div
            className="glass"
            style={{
              padding: "1.5rem",
              borderRadius: "var(--radius-lg)",
            }}
          >
            <h3 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "1.5rem", color: "var(--fg)" }}>
              📊 Similarity Result
            </h3>
            
            {/* Score Display */}
            <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
              <div 
                style={{ 
                  fontSize: "3rem", 
                  fontWeight: 800, 
                  color: getSimilarityColor(result.similarity_score),
                  marginBottom: "0.25rem"
                }}
              >
                {(result.similarity_score * 100).toFixed(1)}%
              </div>
              <div 
                style={{ 
                  fontSize: "1.1rem", 
                  fontWeight: 600, 
                  color: getSimilarityColor(result.similarity_score),
                  marginBottom: "0.5rem"
                }}
              >
                {getSimilarityLabel(result.similarity_score)}
              </div>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  background: `${getSimilarityColor(result.similarity_score)}22`,
                  border: `1px solid ${getSimilarityColor(result.similarity_score)}44`,
                  borderRadius: "9999px",
                  padding: "0.25rem 0.75rem",
                  fontSize: "0.8rem",
                  color: getSimilarityColor(result.similarity_score),
                  fontWeight: 600,
                }}
              >
                <span>cosine similarity</span>
                <span style={{ fontWeight: 800 }}>{result.similarity_score.toFixed(4)}</span>
              </div>
            </div>

            {/* Text Comparison */}
            <div
              style={{
                background: "rgba(0,0,0,0.2)",
                borderRadius: "var(--radius-md)",
                padding: "1rem",
              }}
            >
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div>
                  <h4 style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--fg)" }}>
                    Text 1:
                  </h4>
                  <div 
                    style={{ 
                      fontSize: "0.85rem", 
                      color: "var(--muted)", 
                      background: "rgba(0,0,0,0.3)", 
                      padding: "0.75rem", 
                      borderRadius: "var(--radius-md)",
                      lineHeight: 1.5,
                      maxHeight: "120px",
                      overflowY: "auto"
                    }}
                  >
                    {result.text1}
                  </div>
                </div>
                <div>
                  <h4 style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--fg)" }}>
                    Text 2:
                  </h4>
                  <div 
                    style={{ 
                      fontSize: "0.85rem", 
                      color: "var(--muted)", 
                      background: "rgba(0,0,0,0.3)", 
                      padding: "0.75rem", 
                      borderRadius: "var(--radius-md)",
                      lineHeight: 1.5,
                      maxHeight: "120px",
                      overflowY: "auto"
                    }}
                  >
                    {result.text2}
                  </div>
                </div>
              </div>
            </div>

            {/* Info */}
            <div style={{ marginTop: "1rem", fontSize: "0.8rem", color: "var(--muted)", lineHeight: 1.5 }}>
              <p>
                Cosine similarity measures the cosine of the angle between two text vectors in high-dimensional space.
                Values closer to 1 indicate more similar semantic meaning, while values closer to 0 indicate different meanings.
              </p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!result && !error && !loading && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--muted)",
              gap: "0.75rem",
              paddingTop: "2rem",
            }}
          >
            <span style={{ fontSize: "3rem" }}>📊</span>
            <p style={{ fontSize: "1rem", textAlign: "center" }}>
              Enter two texts above to compare their <strong style={{ color: "var(--fg)" }}>semantic similarity</strong>.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}