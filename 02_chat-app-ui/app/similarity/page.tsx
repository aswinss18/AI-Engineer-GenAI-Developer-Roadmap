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
        throw new Error('Failed to calculate similarity');
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
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getSimilarityLabel = (score: number) => {
    if (score >= 0.8) return 'Very Similar';
    if (score >= 0.6) return 'Moderately Similar';
    if (score >= 0.4) return 'Somewhat Similar';
    return 'Not Similar';
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-8">
            <button
              onClick={() => router.push('/')}
              className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Menu
            </button>
            <h1 className="text-3xl font-bold text-gray-900">
              Cosine Similarity Checker
            </h1>
            <div className="w-24"></div> {/* Spacer for centering */}
          </div>
          
          <div className="grid md:grid-cols-2 gap-6 mb-6">
            <div>
              <label htmlFor="text1" className="block text-sm font-medium text-gray-700 mb-2">
                Text 1
              </label>
              <textarea
                id="text1"
                value={text1}
                onChange={(e) => setText1(e.target.value)}
                className="w-full h-32 p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                placeholder="Enter the first text..."
              />
            </div>
            
            <div>
              <label htmlFor="text2" className="block text-sm font-medium text-gray-700 mb-2">
                Text 2
              </label>
              <textarea
                id="text2"
                value={text2}
                onChange={(e) => setText2(e.target.value)}
                className="w-full h-32 p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                placeholder="Enter the second text..."
              />
            </div>
          </div>

          <div className="text-center mb-6">
            <button
              onClick={calculateSimilarity}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 px-6 rounded-md transition-colors"
            >
              {loading ? 'Calculating...' : 'Calculate Similarity'}
            </button>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
              <p className="text-red-600">{error}</p>
            </div>
          )}

          {result && (
            <div className="bg-gray-50 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Similarity Result</h2>
              
              <div className="text-center mb-4">
                <div className={`text-4xl font-bold ${getSimilarityColor(result.similarity_score)}`}>
                  {(result.similarity_score * 100).toFixed(1)}%
                </div>
                <div className={`text-lg font-medium ${getSimilarityColor(result.similarity_score)}`}>
                  {getSimilarityLabel(result.similarity_score)}
                </div>
              </div>

              <div className="bg-white rounded-md p-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <h3 className="font-medium text-gray-700 mb-2">Text 1:</h3>
                    <p className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                      {result.text1}
                    </p>
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-700 mb-2">Text 2:</h3>
                    <p className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                      {result.text2}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-4 text-sm text-gray-500">
                <p>
                  Cosine similarity measures the cosine of the angle between two text vectors.
                  Values range from 0 (completely different) to 1 (identical).
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}