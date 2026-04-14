from pydantic import BaseModel, Field
from typing import Optional, List

class UploadResponse(BaseModel):
    job_id: str
    filename: str
    status: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    message: Optional[str] = None

class AskRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    top_k: int = Field(5, ge=1, le=20)

class ChunkSource(BaseModel):
    text: str
    similarity_score: float
    doc_id: str
    chunk_index: int

class AskResponse(BaseModel):
    answer: str
    sources: List[ChunkSource]
    latency_ms: float