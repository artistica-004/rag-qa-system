# RAG QA System

A **Retrieval-Augmented Generation** question-answering system that lets you upload documents (PDF/TXT) and ask questions about them. The system uses FAISS for semantic search and Groq LLMs for fast, accurate answers.

## Quick Start

### 1. Setup

```bash
# Clone/navigate to project
cd rag-qa-system

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Or (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Create `.env` file in project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Get your free Groq API key from: https://console.groq.com

### 3. Run the Server

```bash
uvicorn app.main:app --reload
```

Server runs at: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## API Endpoints

### Upload Document
```
POST /upload
Content-Type: multipart/form-data

Parameters:
- file: (binary) PDF or TXT file
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "status": "queued"
}
```

**Check Processing Status:**
```
GET /status/{job_id}
```

---

### Ask Question
```
POST /ask
Content-Type: application/json

Body:
{
  "query": "What is the main topic?",
  "top_k": 5
}
```

**Parameters:**
- `query` (required): 3-500 characters
- `top_k`: 1-20 results to retrieve (default: 5)

**Response:**
```json
{
  "answer": "The main topic is...",
  "sources": [
    {
      "text": "Relevant excerpt from document...",
      "similarity_score": 0.8523,
      "doc_id": "550e8400-...",
      "chunk_index": 3
    }
  ],
  "latency_ms": 1245.67
}
```

---

## Rate Limits

- **Upload:** 5 requests per minute
- **Ask:** 20 requests per minute

Limits are per IP address.

---

## How It Works

### 1. Document Processing
- Extracts text from PDFs using PyPDF2
- UTF-8 text files supported
- Removes extra whitespace

### 2. Chunking
- **Chunk Size:** 512 words (~2-3 paragraphs)
- **Overlap:** 64 words (prevents losing context at boundaries)
- Why? Captures complete ideas while maintaining retrieval precision

### 3. Embeddings
- Model: `all-MiniLM-L6-v2` (fast, CPU-only, free)
- Converts text chunks to 384-dimensional vectors

### 4. Retrieval
- Uses FAISS (Facebook AI Similarity Search)
- Cosine similarity matching
- Top-k chunks returned with scores

### 5. Answer Generation
- Prompt includes retrieved context + user query
- Uses Groq Llama 3.3 (fast, accurate)
- Latency ~1000-1600ms (mostly LLM API time)

---

## System Design Decisions

### Chunk Size: 512 Words with 64-Word Overlap

**Why not smaller?**
- 256 words: Sentences get cut mid-thought, answers lack context
- 512 words: Best balance — captures one complete idea
- Overlap prevents losing information at chunk boundaries

**Tested configs:**
- 256 words → Too small, poor context
- 1024 words → Too large, retrieval pulls irrelevant sections
- **512 + 64 overlap → ✅ Best performance**

See [docs/explanation.md](docs/explanation.md) for detailed analysis.

---

## Known Limitations

### 1. Multi-Hop Queries (Failure Case)

**Problem:** Questions requiring reasoning across multiple chunks often fail.

**Example:**
```
Q: "What is the conclusion of the section that introduces neural networks?"
```

This requires finding the introduction first, then the conclusion — but they may be in different chunks. Single-stage top-k retrieval scores each independently and might miss the conclusion chunk.

**Why?** The conclusion chunk contains "conclusion" but not "neural networks," so similarity score (~0.41) falls below useful threshold.

**Workaround:** Use more specific queries or increase `top_k`.

---

## Metrics

### End-to-End Query Latency

Tracked from `/ask` request → JSON response.

**Observed Breakdown** (10-page PDF):
- Query embedding generation: ~85ms
- FAISS similarity search (top-5 from ~200 chunks): ~12ms
- Groq LLM API call: ~800–1600ms
- **Total: ~900–1700ms**

**Key Finding:** LLM dominates (>85% of time). FAISS retrieval is negligible. Optimization efforts should focus on prompt engineering and model selection, not search speed.

---

## Running Tests

```bash
pytest tests/ -v
```

Current tests:
- API health check
- File type validation
- TXT upload and processing
- Query handling without documents

---

## File Structure

```
rag-qa-system/
├── app/
│   ├── main.py           # FastAPI app + endpoints
│   ├── ingestion.py      # Text extraction + chunking + embeddings
│   ├── retriever.py      # FAISS vector store
│   ├── llm.py            # Groq LLM wrapper
│   ├── models.py         # Pydantic request/response schemas
│   └── rate_limiter.py   # slowapi rate limiting
├── docs/
│   └── explanation.md    # Deep dive into design decisions
├── tests/
│   └── test_api.py       # API tests
├── vector_store/         # FAISS index + metadata (auto-created)
├── uploads/              # Uploaded documents (auto-created)
├── requirements.txt
├── .env                  # (create this — add GROQ_API_KEY)
└── README.md
```

---

## Troubleshooting

### 422 Validation Error on /ask

**Cause:** Invalid request body

**Check:**
- `query` is 3-500 characters
- `top_k` is 1-20 (optional)

**Example Fix:**
```json
{
  "query": "What is machine learning?",
  "top_k": 5
}
```

### "No documents uploaded yet"

**Cause:** No index exists — upload a document first

```bash
# Upload something, wait for status="done"
POST /upload (file)
GET /status/{job_id}  # Check until done
POST /ask             # Now works
```

### "No relevant chunks found"

**Cause:** Query doesn't match document content

**Try:**
- Rephrase the query more specifically
- Increase `top_k` to 10-20
- Check the uploaded document is correct

---

## Dependencies

- **Framework:** FastAPI (web), Uvicorn (server)
- **Vector DB:** FAISS (similarity search)
- **Embeddings:** SentenceTransformers
- **LLM:** Groq API (Llama 3.3)
- **Validation:** Pydantic
- **Rate Limiting:** slowapi
- **PDF Parsing:** PyPDF2
- **Utilities:** python-dotenv, requests, numpy

See [requirements.txt](requirements.txt) for exact versions.

---

## License

MIT

---

## Questions?

See [docs/explanation.md](docs/explanation.md) for detailed system design analysis.
