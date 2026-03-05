'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface SearchResult {
  text: string;
  score: number;
}

interface SearchResponse {
  query: string;
  results: SearchResult[];
}

export default function SemanticSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const performSearch = async () => {
    if (!query.trim()) {
      setError('Please enter a search query');
      return;
    }

    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('http://localhost:8000/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to perform search');
      }

      const data: SearchResponse = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return '#4ade80';
    if (score >= 0.6) return '#facc15';
    if (score >= 0.4) return '#f97316';
    return '#f87171';
  };

  const getScoreLabel = (score: number) => {
    if (score >= 0.8) return 'Highly Relevant';
    if (score >= 0.6) return 'Very Relevant';
    if (score >= 0.4) return 'Relevant';
    return 'Somewhat Relevant';
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      performSearch();
    }
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
          <span style={{ fontSize: "1.3rem" }}>🔍</span>
          <span style={{ fontWeight: 700, fontSize: "1rem" }}>Semantic Search</span>
          <span
            style={{
              fontSize: "0.68rem",
              padding: "0.15rem 0.55rem",
              borderRadius: "9999px",
              background: "#06b6d422",
              color: "#06b6d4",
              border: "1px solid #06b6d444",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              fontWeight: 600,
            }}
          >
            Document Search
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
          {loading ? "Searching…" : "Ready"}
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
        {/* Search Section */}
        <div
          className="glass"
          style={{
            padding: "1.5rem",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <h2 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "1rem", color: "var(--fg)" }}>
            🔍 Search Documents
          </h2>
          <p style={{ color: "var(--muted)", marginBottom: "1.5rem", lineHeight: 1.6, fontSize: "0.9rem" }}>
            Enter your search query to find the most semantically similar documents using AI embeddings. 
            The search understands context and meaning, not just keywords.
          </p>
          
          <div style={{ marginBottom: "1.5rem" }}>
            <label style={{ display: "block", fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--fg)" }}>
              Search Query
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter your search query... (e.g., 'machine learning algorithms', 'healthy eating tips', 'space exploration')"
              disabled={loading}
              style={{
                width: "100%",
                minHeight: "80px",
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
                (e.currentTarget as HTMLElement).style.borderColor = "#06b6d4";
              }}
              onBlur={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
              }}
            />
            <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginTop: "0.5rem" }}>
              Press Enter to search, or use the button below
            </div>
          </div>

          <button
            onClick={performSearch}
            disabled={loading || !query.trim()}
            className="accent-btn"
            style={{
              width: "100%",
              padding: "0.75rem",
              fontSize: "1rem",
              fontWeight: 600,
            }}
          >
            {loading ? "Searching Documents…" : "Search Documents"}
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
        {results && (
          <div
            className="glass"
            style={{
              padding: "1.5rem",
              borderRadius: "var(--radius-lg)",
            }}
          >
            <h3 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "1rem", color: "var(--fg)" }}>
              📋 Search Results for "{results.query}"
            </h3>
            
            <div style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "1.5rem" }}>
              Found {results.results.length} relevant documents
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {results.results.map((result, index) => (
                <div
                  key={index}
                  style={{
                    background: "rgba(0,0,0,0.2)",
                    borderRadius: "var(--radius-md)",
                    padding: "1.25rem",
                    border: "1px solid var(--border)",
                    transition: "border-color 0.2s",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.borderColor = getScoreColor(result.score);
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                  }}
                >
                  {/* Result Header */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span style={{ fontSize: "1.1rem" }}>📄</span>
                      <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--fg)" }}>
                        Result #{index + 1}
                      </span>
                    </div>
                    
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                      <div
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "0.4rem",
                          background: `${getScoreColor(result.score)}22`,
                          border: `1px solid ${getScoreColor(result.score)}44`,
                          borderRadius: "9999px",
                          padding: "0.2rem 0.6rem",
                          fontSize: "0.75rem",
                          color: getScoreColor(result.score),
                          fontWeight: 600,
                        }}
                      >
                        <span>{getScoreLabel(result.score)}</span>
                      </div>
                      
                      <div 
                        style={{ 
                          fontSize: "1.1rem", 
                          fontWeight: 700, 
                          color: getScoreColor(result.score)
                        }}
                      >
                        {(result.score * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>

                  {/* Result Content */}
                  <div 
                    style={{ 
                      fontSize: "0.9rem", 
                      color: "var(--fg)", 
                      lineHeight: 1.6,
                      background: "rgba(0,0,0,0.3)",
                      padding: "1rem",
                      borderRadius: "var(--radius-md)",
                      border: `1px solid ${getScoreColor(result.score)}22`,
                    }}
                  >
                    {result.text}
                  </div>

                  {/* Score Details */}
                  <div style={{ marginTop: "0.75rem", fontSize: "0.8rem", color: "var(--muted)" }}>
                    Similarity Score: <span style={{ color: getScoreColor(result.score), fontWeight: 600 }}>
                      {result.score.toFixed(4)}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Search Info */}
            <div style={{ marginTop: "1.5rem", fontSize: "0.8rem", color: "var(--muted)", lineHeight: 1.5 }}>
              <p>
                Results are ranked by semantic similarity using OpenAI embeddings. Higher scores indicate 
                documents that are more contextually relevant to your search query.
              </p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!results && !error && !loading && (
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
            <span style={{ fontSize: "3rem" }}>🔍</span>
            <p style={{ fontSize: "1rem", textAlign: "center" }}>
              Enter a search query above to find <strong style={{ color: "var(--fg)" }}>semantically similar</strong> documents.
            </p>
            <div style={{ fontSize: "0.85rem", textAlign: "center", maxWidth: "400px" }}>
              Try searching for topics like "artificial intelligence", "healthy recipes", "space exploration", or any other subject.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}