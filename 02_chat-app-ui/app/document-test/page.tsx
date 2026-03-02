'use client';

import { useState } from 'react';

export default function DocumentTestPage() {
  const [document, setDocument] = useState('');
  const [query, setQuery] = useState('');
  const [uploadStatus, setUploadStatus] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!document.trim()) {
      setUploadStatus('Please enter a document');
      return;
    }

    setLoading(true);
    setUploadStatus('Uploading...');

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `text=${encodeURIComponent(document)}`,
      });

      const data = await response.json();
      setUploadStatus(data.message || 'Document uploaded successfully!');
    } catch (error) {
      setUploadStatus('Error uploading document: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const handleRetrieve = async () => {
    if (!query.trim()) {
      return;
    }

    setLoading(true);
    setResults([]);

    try {
      const response = await fetch('http://localhost:8000/retrieve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `query=${encodeURIComponent(query)}&k=3`,
      });

      const data = await response.json();
      setResults(data.results || []);
    } catch (error) {
      console.error('Error retrieving:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen p-8 bg-gray-50">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Document Upload & Retrieve Test</h1>

        {/* Upload Section */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">1. Upload Document</h2>
          <textarea
            value={document}
            onChange={(e) => setDocument(e.target.value)}
            placeholder="Paste your document text here..."
            className="w-full h-48 p-3 border border-gray-300 rounded-lg mb-4 font-mono text-sm"
          />
          <button
            onClick={handleUpload}
            disabled={loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Uploading...' : 'Upload Document'}
          </button>
          {uploadStatus && (
            <p className="mt-3 text-sm text-gray-700">{uploadStatus}</p>
          )}
        </div>

        {/* Retrieve Section */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">2. Retrieve Chunks</h2>
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleRetrieve()}
              placeholder="Enter your search query..."
              className="flex-1 p-3 border border-gray-300 rounded-lg"
            />
            <button
              onClick={handleRetrieve}
              disabled={loading}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400"
            >
              {loading ? 'Searching...' : 'Retrieve'}
            </button>
          </div>
        </div>

        {/* Results Section */}
        {results.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Results</h2>
            <div className="space-y-4">
              {results.map((result, index) => (
                <div
                  key={index}
                  className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition"
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-semibold text-gray-600">
                      Chunk {index + 1}
                    </span>
                    <span className="text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      Score: {result.score}
                    </span>
                  </div>
                  <p className="text-gray-800 whitespace-pre-wrap">{result.chunk}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Sample Document */}
        <div className="bg-blue-50 rounded-lg p-6 mt-6">
          <h3 className="font-semibold mb-2">Sample Document (for testing):</h3>
          <p className="text-sm text-gray-700 mb-2">
            Copy and paste this sample text to test the functionality:
          </p>
          <pre className="text-xs bg-white p-3 rounded border overflow-x-auto">
{`Artificial Intelligence (AI) is transforming the world.
Machine learning is a subset of AI that enables computers to learn from data.

Natural Language Processing (NLP) allows computers to understand human language.
Deep learning uses neural networks with multiple layers.

Computer vision enables machines to interpret visual information.
Reinforcement learning trains agents through rewards and penalties.

AI applications include healthcare, finance, and autonomous vehicles.
Ethics in AI is becoming increasingly important as technology advances.`}
          </pre>
        </div>
      </div>
    </div>
  );
}
