# Text Similarity Engine

A FastAPI-based service that calculates cosine similarity between two texts using OpenAI embeddings.

## Features

- **Cosine Similarity Calculation**: Compare two texts and get their similarity score (0-1)
- **OpenAI Embeddings**: Uses `text-embedding-3-small` model for high-quality text embeddings
- **FastAPI REST API**: Clean API endpoint for similarity calculations
- **CORS Support**: Configured for frontend integration

## API Endpoint

### POST `/api/similarity`

Calculate cosine similarity between two texts.

**Request Body:**
```json
{
  "text1": "I love playing football",
  "text2": "I enjoy soccer"
}
```

**Response:**
```json
{
  "similarity_score": 0.8234567,
  "text1": "I love playing football",
  "text2": "I enjoy soccer"
}
```

## Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Run the server:**
   ```bash
   uv run uvicorn main:app --reload --port 8000
   ```

The API will be available at `http://localhost:8000`

## Usage

### Example with curl:
```bash
curl -X POST "http://localhost:8000/api/similarity" \
     -H "Content-Type: application/json" \
     -d '{
       "text1": "I love playing football",
       "text2": "I enjoy soccer"
     }'
```

### Example with Python:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/similarity",
    json={
        "text1": "I love playing football",
        "text2": "I enjoy soccer"
    }
)

result = response.json()
print(f"Similarity: {result['similarity_score']:.2%}")
```

## How It Works

1. **Text Embedding**: Each input text is converted to a high-dimensional vector using OpenAI's embedding model
2. **Cosine Similarity**: The cosine of the angle between the two vectors is calculated
3. **Score Interpretation**:
   - 1.0: Identical texts
   - 0.8+: Very similar
   - 0.6-0.8: Moderately similar
   - 0.4-0.6: Somewhat similar
   - <0.4: Not similar

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.