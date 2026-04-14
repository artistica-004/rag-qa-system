import os
import re
import PyPDF2
from sentence_transformers import SentenceTransformer

# Load embedding model once when app starts
# all-MiniLM-L6-v2: free, fast, runs on CPU, no API key needed
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


def extract_text(filepath: str, extension: str) -> str:
    """Extract raw text from PDF or TXT file."""
    if extension == ".pdf":
        text = ""
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    elif extension == ".txt":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file type: {extension}")


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list:
    """
    Split text into overlapping chunks by word count.
    512 words = ~2-3 paragraphs, enough for one complete idea.
    64 word overlap prevents losing context at chunk boundaries.
    """
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def embed_chunks(chunks: list) -> list:
    """Convert text chunks into vector embeddings."""
    embeddings = embedding_model.encode(
        chunks,
        show_progress_bar=False,
        convert_to_numpy=True
    )
    return embeddings.tolist()