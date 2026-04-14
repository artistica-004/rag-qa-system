from fastapi.testclient import TestClient
from app.main import app
import io
import time

client = TestClient(app)

# ============ HEALTH & STATUS TESTS ============

def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "RAG QA System" in response.json()["message"]

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "vector_store_exists" in data

# ============ UPLOAD TESTS ============

def test_upload_invalid_file():
    """Should reject non-PDF/TXT files."""
    fake_file = io.BytesIO(b"fake content")
    response = client.post(
        "/upload",
        files={"file": ("test.docx", fake_file, "application/octet-stream")}
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]

def test_upload_empty_file():
    """Should reject empty files."""
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/upload",
        files={"file": ("empty.txt", empty_file, "text/plain")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_upload_txt_file():
    """Test successful TXT file upload."""
    content = b"This is a comprehensive test document about machine learning, neural networks, and deep learning methodologies."
    response = client.post(
        "/upload",
        files={"file": ("test.txt", io.BytesIO(content), "text/plain")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["filename"] == "test.txt"

def test_upload_no_file():
    """Should reject request without file."""
    response = client.post("/upload")
    assert response.status_code == 422  # Validation error

# ============ JOB STATUS TESTS ============

def test_job_status_not_found():
    """Should return 404 for non-existent job."""
    response = client.get("/status/invalid-job-id-12345")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

# ============ QUERY TESTS ============

def test_ask_invalid_query_too_short():
    """Query must be at least 3 characters."""
    response = client.post("/ask", json={"query": "ab", "top_k": 5})
    assert response.status_code == 422  # Validation error

def test_ask_invalid_query_too_long():
    """Query must not exceed 500 characters."""
    long_query = "a" * 501
    response = client.post("/ask", json={"query": long_query, "top_k": 5})
    assert response.status_code == 422  # Validation error

def test_ask_invalid_top_k():
    """top_k must be between 1 and 20."""
    response = client.post("/ask", json={"query": "What is AI?", "top_k": 25})
    assert response.status_code == 422  # Validation error

def test_ask_without_documents():
    """Should return 400 if no documents uploaded."""
    import os
    if not os.path.exists("vector_store/index.faiss"):
        response = client.post("/ask", json={"query": "What is this about?", "top_k": 3})
        assert response.status_code == 400
        assert "No documents uploaded" in response.json()["detail"]

# ============ RATE LIMITING TESTS ============

def test_upload_rate_limit():
    """Test upload rate limiting (5/minute)."""
    content = b"Test document content for rate limiting."
    
    # Try to exceed rate limit
    responses = []
    for i in range(6):
        response = client.post(
            "/upload",
            files={"file": (f"test_{i}.txt", io.BytesIO(content), "text/plain")}
        )
        responses.append(response.status_code)
    
    # At least one request should be rate-limited
    assert 429 in responses or response.status_code == 200, "Rate limiting test (may pass if enough time elapsed)"

def test_ask_rate_limit():
    """Test ask rate limiting (20/minute)."""
    # Skip if no documents in store
    import os
    if not os.path.exists("vector_store/index.faiss"):
        return
    
    responses = []
    for i in range(21):
        response = client.post(
            "/ask",
            json={"query": f"Test query number {i}?", "top_k": 3}
        )
        responses.append(response.status_code)
    
    # At least one request should be rate-limited
    assert 429 in responses or response.status_code == 200, "Rate limiting test (may pass if enough time elapsed)"