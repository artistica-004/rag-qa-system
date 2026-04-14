import os
import uuid
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.models import UploadResponse, AskRequest, AskResponse, JobStatusResponse, ChunkSource
from app.rate_limiter import limiter
from app.ingestion import extract_text, chunk_text, embed_chunks
from app.retriever import add_to_index, search
from app.llm import generate_answer

job_store: dict = {}

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".txt"}

app = FastAPI(title="RAG QA System", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def process_document(filepath: str, doc_id: str, extension: str):
    try:
        job_store[doc_id]["status"] = "processing"
        text = extract_text(filepath, extension)
        if not text.strip():
            job_store[doc_id] = {"status": "failed", "message": "Could not extract text"}
            return
        chunks = chunk_text(text)
        embeddings = embed_chunks(chunks)
        metadata = [
            {"doc_id": doc_id, "chunk_index": i, "text": chunk}
            for i, chunk in enumerate(chunks)
        ]
        add_to_index(embeddings, metadata)
        job_store[doc_id]["status"] = "done"
        job_store[doc_id]["message"] = f"Processed {len(chunks)} chunks"
    except Exception as e:
        job_store[doc_id] = {"status": "failed", "message": str(e)}

@app.post("/upload", response_model=UploadResponse)
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    filename = file.filename.strip()
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Only PDF and TXT are allowed."
        )

    doc_id = str(uuid.uuid4())
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(UPLOAD_DIR, f"{doc_id}{ext}")

    # Read file content
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    # Write to disk
    with open(save_path, "wb") as f:
        f.write(content)

    job_store[doc_id] = {"status": "queued", "message": "Waiting to process"}
    background_tasks.add_task(process_document, save_path, doc_id, ext)

    return UploadResponse(job_id=doc_id, filename=filename, status="queued")

@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    job = job_store[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        message=job.get("message")
    )

@app.post("/ask", response_model=AskResponse)
@limiter.limit("20/minute")
async def ask_question(request: Request, body: AskRequest):
    from app.ingestion import embedding_model
    if not os.path.exists("vector_store/index.faiss"):
        raise HTTPException(
            status_code=400,
            detail="No documents uploaded yet. Please upload a document first."
        )
    query_embedding = embedding_model.encode(
        [body.query], convert_to_numpy=True
    ).tolist()[0]
    results = search(query_embedding, top_k=body.top_k)
    if not results:
        raise HTTPException(status_code=404, detail="No relevant chunks found.")
    chunks_text = [meta["text"] for meta, score in results]
    answer, latency_ms = generate_answer(body.query, chunks_text)
    sources = [
        ChunkSource(
            text=meta["text"][:300] + "..." if len(meta["text"]) > 300 else meta["text"],
            similarity_score=round(score, 4),
            doc_id=meta["doc_id"],
            chunk_index=meta["chunk_index"]
        )
        for meta, score in results
    ]
    return AskResponse(
        answer=answer,
        sources=sources,
        latency_ms=round(latency_ms, 2)
    )

@app.get("/")
async def root():
    return {"message": "RAG QA System is running. Visit /docs for API documentation."}