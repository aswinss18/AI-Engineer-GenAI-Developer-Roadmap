# JSON Serialization Fixes

## Problem
The streaming API was failing with `TypeError: Object of type float32 is not JSON serializable` because numpy arrays and numpy scalar types (like `float32`) cannot be directly serialized to JSON.

## Root Cause
Several modules were returning numpy types in their data structures:
- `vector_store.py`: FAISS search returns `float32` distances
- `hybrid_search.py`: Score calculations using numpy operations
- `reranker.py`: Cosine similarity calculations with numpy
- `keyword_search.py`: TF-IDF score calculations
- `multi_document_context.py`: Statistical calculations

## Fixes Applied

### 1. Vector Store (`core/vector_store.py`)
```python
# Before
similarity_score = 1.0 / (1.0 + distance)
"distance": float(distance)

# After  
similarity_score = 1.0 / (1.0 + float(distance))  # Convert to Python float
"distance": float(distance)  # Explicit conversion
```

### 2. Hybrid Search (`core/hybrid_search.py`)
```python
# Before
"hybrid_score": hybrid_score,
"vector_weight": vector_weight,
"avg_hybrid_score": round(avg_hybrid_score, 3),

# After
"hybrid_score": float(hybrid_score),  # Ensure Python float
"vector_weight": float(vector_weight),
"avg_hybrid_score": float(round(avg_hybrid_score, 3)),
```

### 3. Reranker (`core/reranker.py`)
```python
# Before
return dot_product / (norm_a * norm_b)
"cosine_similarity": cosine_score,

# After
return float(dot_product / (norm_a * norm_b))  # Ensure Python float
"cosine_similarity": float(cosine_score),
```

### 4. Keyword Search (`core/keyword_search.py`)
```python
# Before
return score
"keyword_score": score,

# After
return float(score)  # Ensure Python float
"keyword_score": float(score),
```

### 5. Multi-Document Context (`core/multi_document_context.py`)
```python
# Before
"coverage_percentage": round(coverage_percentage, 1),
"avg_score": doc_scores[doc_name]

# After
"coverage_percentage": float(round(coverage_percentage, 1)),
"avg_score": float(doc_scores[doc_name])
```

## Verification Strategy

### Type Conversion Rules
1. **All numeric values** returned in API responses must be Python native types
2. **Numpy scalars** must be converted using `float()` or `int()`
3. **Calculations** should convert results immediately after numpy operations
4. **Statistical functions** must ensure return types are JSON serializable

### Testing Approach
```python
import json

# Test data structure
data = {"score": float(numpy_value)}  # ✅ Correct
data = {"score": numpy_value}         # ❌ Will fail

# Verify serialization
try:
    json.dumps(data)  # Should not raise TypeError
except TypeError as e:
    # Fix any remaining numpy types
    pass
```

## Impact
- **Streaming API**: Now works without JSON serialization errors
- **All Endpoints**: Return properly serialized JSON responses
- **UI Integration**: Receives valid JSON data for display
- **Performance**: Minimal impact (type conversion is fast)

## Prevention
- Always use `float()` when returning numpy scalar values
- Test JSON serialization in development
- Use type hints to catch potential issues
- Consider using `json.dumps()` in tests to verify serialization