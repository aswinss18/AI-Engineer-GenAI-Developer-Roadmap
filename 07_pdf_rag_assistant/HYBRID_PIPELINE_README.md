# Hybrid RAG Pipeline

## Overview

This implementation features an advanced hybrid RAG pipeline that combines vector similarity search with keyword-based search, followed by intelligent reranking and context compression for superior retrieval precision and coverage.

## Pipeline Architecture

```
Query
  ↓
Hybrid Search (Vector + Keyword)
  ├── Vector Search (top 8 candidates)
  └── Keyword Search (top 8 candidates)
  ↓
Combine & Deduplicate Results
  ↓
Rerank using Cosine Similarity
  ↓
Context Compression
  ↓
Smart Context Selection (best 3-5 chunks)
  ↓
Send to LLM
```

## Key Features

### 1. Hybrid Retrieval System
- **Vector Search**: FAISS-based semantic similarity matching
- **Keyword Search**: TF-IDF based exact term matching
- **Smart Combination**: Deduplication and score normalization
- **Multi-method Boost**: 20% score boost for chunks found by both methods

### 2. Advanced Keyword Search
- **Inverted Index**: Fast term lookup with document frequencies
- **TF-IDF Scoring**: Term frequency × Inverse document frequency
- **Query Tokenization**: Intelligent text preprocessing
- **Matched Terms Tracking**: Shows which keywords triggered results

### 3. Hybrid Scoring System
- **Normalized Scores**: Both vector and keyword scores normalized to 0-1 range
- **Weighted Combination**: 60% vector + 40% keyword (configurable)
- **Multi-method Bonus**: Extra scoring for chunks found by both systems
- **Transparent Metrics**: Full score breakdown in results

### 4. Enhanced UI Integration
- **Search Type Badges**: Visual indicators for Vector/Keyword/Hybrid results
- **Hybrid Statistics**: Shows distribution across search methods
- **Matched Keywords**: Displays which terms triggered keyword matches
- **Score Transparency**: Multiple score types (hybrid, vector, keyword, final)

## Implementation Details

### Core Components

1. **`core/keyword_search.py`**
   - `KeywordSearcher`: Main keyword search engine
   - `build_index()`: Creates inverted index from documents
   - `search()`: TF-IDF based keyword search
   - Tokenization and scoring algorithms

2. **`core/hybrid_search.py`**
   - `hybrid_search()`: Combines vector and keyword results
   - Score normalization and weighting
   - Deduplication by chunk identity
   - Multi-method detection and boosting

3. **`core/vector_store.py`**
   - Enhanced to build keyword index automatically
   - Maintains both vector and keyword search capabilities
   - Integrated persistence for both search types

4. **`core/rag_pipeline.py`**
   - Updated pipeline functions use hybrid search
   - Enhanced metadata with hybrid statistics
   - Improved source quality information

### Configuration

```python
# Hybrid search settings
VECTOR_K = 8               # Vector search candidates
KEYWORD_K = 8              # Keyword search candidates
VECTOR_WEIGHT = 0.6        # Vector score weight
KEYWORD_WEIGHT = 0.4       # Keyword score weight
MULTI_METHOD_BOOST = 1.2   # Boost for both methods

# Reranking settings
RERANKED_TOP_K = 5         # After reranking
FINAL_CHUNKS = 3-5         # Context selection

# Compression settings
MAX_CHUNK_LENGTH = 600     # Per chunk limit
MAX_CONTEXT_LENGTH = 2500  # Total context limit
```

## Benefits Over Vector-Only Search

### Improved Coverage
- **Semantic + Lexical**: Captures both meaning and exact terms
- **Query Robustness**: Works well for both conceptual and specific queries
- **Terminology Matching**: Finds exact technical terms and acronyms
- **Fallback Capability**: Keyword search when vector search fails

### Enhanced Precision
- **Multi-method Validation**: Chunks found by both methods are highly relevant
- **Diverse Results**: Combines different retrieval paradigms
- **Query-adaptive**: Automatically balances semantic vs. lexical matching
- **Reduced False Negatives**: Less likely to miss relevant content

### Better User Experience
- **Transparent Results**: Shows how each chunk was found
- **Keyword Highlighting**: Displays matched terms
- **Search Statistics**: Detailed breakdown of retrieval methods
- **Quality Indicators**: Multiple scoring dimensions

## Usage Examples

### Hybrid Search API
```python
from core.hybrid_search import hybrid_search

# Perform hybrid search
results = hybrid_search(
    query="machine learning algorithms",
    vector_k=8,
    keyword_k=8,
    vector_weight=0.6,
    keyword_weight=0.4
)

# Results include hybrid scores and search type information
for result in results:
    print(f"Text: {result['text'][:100]}...")
    print(f"Hybrid Score: {result['hybrid_score']}")
    print(f"Search Types: {result['search_types']}")
    if 'matched_terms' in result:
        print(f"Keywords: {result['matched_terms']}")
```

### Pipeline Integration
The hybrid search is automatically used in all question-answering functions:

```python
# Streaming with hybrid pipeline
for chunk_data in ask_question_stream_with_sources(question):
    # Returns enhanced metadata including:
    # - hybrid_stats with method distribution
    # - source search_types and matched_terms
    # - multiple score types (hybrid, vector, keyword)
    pass
```

## Monitoring and Analytics

### Hybrid Search Statistics
- **Total Results**: Combined unique chunks
- **Vector Only**: Chunks found only by vector search
- **Keyword Only**: Chunks found only by keyword search
- **Both Methods**: Chunks found by both (highest quality)
- **Average Scores**: Performance metrics

### UI Indicators
- **Purple "Hybrid" Badge**: Shows hybrid pipeline is active
- **Method Distribution**: Visual breakdown of search types
- **Source Badges**: Vector/Keyword/Both indicators per source
- **Keyword Display**: Shows matched terms for keyword results
- **Score Transparency**: Multiple score types displayed

## Performance Characteristics

### Query Types and Performance
1. **Conceptual Queries**: Vector search dominates, keyword provides validation
2. **Specific Term Queries**: Keyword search leads, vector adds context
3. **Mixed Queries**: Balanced contribution from both methods
4. **Technical Queries**: Keyword search excels at exact terminology

### Computational Overhead
- **Index Building**: One-time cost when documents are added
- **Search Time**: ~2x single method (parallel execution possible)
- **Memory Usage**: Additional inverted index (~10-20% of document size)
- **Quality Gain**: Significant improvement in result relevance

## Testing

Run the test script to verify hybrid features:

```bash
python test_enhanced_pipeline.py
```

## Future Enhancements

1. **Query Analysis**: Automatic weight adjustment based on query type
2. **Semantic Expansion**: Expand queries with synonyms and related terms
3. **Learning Weights**: Adapt vector/keyword weights based on user feedback
4. **Parallel Execution**: Run vector and keyword search concurrently
5. **Advanced Tokenization**: Better handling of technical terms and phrases
6. **Fuzzy Matching**: Handle typos and variations in keyword search