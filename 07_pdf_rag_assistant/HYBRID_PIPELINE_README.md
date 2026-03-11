# Multi-Document Hybrid RAG Pipeline

## Overview

This implementation features an advanced multi-document hybrid RAG pipeline that combines vector similarity search with keyword-based search, intelligent document grouping, cross-document analysis, and comparison reasoning for superior retrieval precision and multi-perspective synthesis.

## Pipeline Architecture

```
Query
  ↓
Hybrid Search (Vector + Keyword)
  ├── Vector Search (top 10 candidates)
  └── Keyword Search (top 10 candidates)
  ↓
Group Chunks by Document
  ↓
Combine & Deduplicate Results
  ↓
Rerank using Cosine Similarity
  ↓
Multi-Document Context Building
  ↓
Cross-Document Analysis & Comparison
  ↓
Specialized Reasoning Prompt
  ↓
Send to LLM
```

## Key Features

### 1. Multi-Document Intelligence
- **Document Grouping**: Automatically groups chunks by source document
- **Cross-Document Analysis**: Compares viewpoints across multiple sources
- **Document Boundaries**: Maintains clear document separation in context
- **Coverage Analysis**: Tracks chunk distribution across documents
- **Comparison Reasoning**: Specialized prompts for multi-document synthesis

### 2. Enhanced Hybrid Retrieval
- **Vector Search**: FAISS-based semantic similarity matching
- **Keyword Search**: TF-IDF based exact term matching
- **Smart Combination**: Deduplication and score normalization
- **Multi-method Boost**: 20% score boost for chunks found by both methods
- **Document-Aware Scoring**: Considers document coverage and distribution

### 3. Intelligent Context Building
- **Structured Context**: Clear document boundaries with headers
- **Multi-Doc Prioritization**: Sorts documents by relevance scores
- **Context Optimization**: Maximizes information within token limits
- **Document Metadata**: Includes coverage, page ranges, and quality metrics

### 4. Comparison & Synthesis
- **Cross-Document Prompts**: Specialized prompts for comparison tasks
- **Viewpoint Analysis**: Identifies agreements and disagreements
- **Source Attribution**: Clear citation of document sources
- **Synthesis Reasoning**: Combines insights from multiple perspectives

## Implementation Details

### Core Components

1. **`core/multi_document_context.py`**
   - `group_chunks_by_document()`: Groups chunks by source document
   - `build_multi_document_context()`: Creates structured multi-doc context
   - `create_comparison_prompt()`: Generates specialized comparison prompts
   - `analyze_document_distribution()`: Analyzes document coverage
   - `extract_document_insights()`: Identifies document relationships

2. **`core/keyword_search.py`**
   - `KeywordSearcher`: TF-IDF based keyword search engine
   - `build_index()`: Creates inverted index from documents
   - Tokenization and scoring algorithms

3. **`core/hybrid_search.py`**
   - `hybrid_search()`: Combines vector and keyword results
   - Score normalization and weighting
   - Multi-method detection and boosting

4. **`core/rag_pipeline.py`**
   - Updated pipeline uses multi-document context building
   - Enhanced metadata with document analysis
   - Cross-document reasoning capabilities

### Multi-Document Context Format

```
Multi-Document Analysis (3 documents: doc1.pdf, doc2.pdf, doc3.pdf)

=== Document: doc1.pdf ===

[Page 5] First relevant chunk from document 1...

[Page 7] Second relevant chunk from document 1...

=== Document: doc2.pdf ===

[Page 12] Relevant chunk from document 2...

=== Document: doc3.pdf ===

[Page 3] Relevant chunk from document 3...
```

### Comparison Prompt Template

```
You are an AI research assistant specializing in multi-document analysis and comparison.

TASK: Analyze the provided documents to answer the question. Pay special attention to:
- Comparing viewpoints across different documents
- Identifying agreements and disagreements between sources
- Synthesizing information from multiple perspectives
- Clearly citing which document supports each point

DOCUMENTS PROVIDED: 3 documents with relevant information
[Multi-document context here]

QUESTION: [User question]

INSTRUCTIONS:
1. Answer using information from the provided documents
2. Compare viewpoints when multiple documents discuss the same topic
3. Clearly indicate which document each piece of information comes from
4. Present both perspectives fairly if documents disagree
5. Synthesize insights from combining multiple sources
6. Use format: "According to [Document Name]..." when citing sources
```

## Configuration

```python
# Multi-document settings
VECTOR_K = 10              # Vector search candidates (increased)
KEYWORD_K = 10             # Keyword search candidates (increased)
RERANKED_TOP_K = 8         # After reranking (increased)
MAX_CONTEXT_LENGTH = 3500  # Total context limit (increased)

# Document analysis
MIN_DOC_COVERAGE = 5       # Minimum percentage for inclusion
MAX_DOCUMENTS = 5          # Maximum documents in context

# Hybrid search settings
VECTOR_WEIGHT = 0.6        # Vector score weight
KEYWORD_WEIGHT = 0.4       # Keyword score weight
MULTI_METHOD_BOOST = 1.2   # Boost for both methods
```

## Benefits Over Single-Document Systems

### Enhanced Coverage
- **Multi-Perspective Analysis**: Captures different viewpoints on topics
- **Comprehensive Context**: Draws from multiple authoritative sources
- **Cross-Validation**: Validates information across documents
- **Broader Knowledge**: Accesses wider range of information

### Improved Analysis Quality
- **Comparative Insights**: Identifies similarities and differences
- **Balanced Perspectives**: Presents multiple viewpoints fairly
- **Source Attribution**: Clear tracking of information sources
- **Synthesis Capability**: Combines insights from multiple sources

### Better User Experience
- **Document Transparency**: Shows which documents contribute to answers
- **Coverage Metrics**: Displays document participation levels
- **Quality Indicators**: Multi-dimensional scoring and analysis
- **Comparison Features**: Specialized handling of comparison queries

## Usage Examples

### Multi-Document Analysis
```python
# The pipeline automatically detects and handles multiple documents
results = ask_question_stream_with_sources(
    "Compare the methodologies discussed in the research papers"
)

# Returns enhanced metadata including:
# - document_analysis: Document count, coverage, distribution
# - context_metadata: Multi-document context information
# - document_insights: Relationships and common themes
```

### Document Comparison Queries
- "Compare the approaches discussed in different documents"
- "What are the main differences between the methodologies?"
- "How do the authors agree or disagree on this topic?"
- "Synthesize the key findings from all sources"

## Monitoring and Analytics

### Multi-Document Metrics
- **Document Count**: Number of documents contributing to answer
- **Coverage Distribution**: Percentage contribution per document
- **Cross-Document Matches**: Chunks found across multiple documents
- **Context Efficiency**: Information density per document

### UI Indicators
- **Green "Multi-Doc" Badge**: Shows multi-document pipeline is active
- **Document Coverage**: Shows percentage contribution per document
- **Cross-Document Analysis**: Visual indicators for multi-doc mode
- **Source Distribution**: Document-wise breakdown of sources

## Performance Characteristics

### Query Types and Multi-Document Performance
1. **Comparison Queries**: Excellent performance with specialized prompts
2. **Synthesis Questions**: Strong cross-document information combining
3. **Specific Lookups**: Efficient document-specific information retrieval
4. **Broad Topics**: Comprehensive coverage across multiple sources

### Computational Considerations
- **Increased Context**: Larger context windows for multi-document analysis
- **Document Grouping**: Additional processing for document organization
- **Comparison Logic**: Enhanced reasoning for cross-document analysis
- **Quality Gains**: Significant improvement in answer comprehensiveness

## Testing

Run the comprehensive test script:

```bash
python test_enhanced_pipeline.py
```

Tests include:
- Multi-document detection and grouping
- Cross-document analysis capabilities
- Document comparison features
- Hybrid search across multiple documents

## Future Enhancements

1. **Document Relationship Mapping**: Identify citations and references between documents
2. **Temporal Analysis**: Consider document publication dates in analysis
3. **Authority Weighting**: Weight documents by credibility and relevance
4. **Conflict Resolution**: Advanced handling of contradictory information
5. **Summary Generation**: Automatic multi-document summaries
6. **Topic Clustering**: Group documents by thematic similarity