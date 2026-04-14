import os
import json
import numpy as np
import faiss

INDEX_PATH = "vector_store/index.faiss"
META_PATH  = "vector_store/meta.json"

def add_to_index(embeddings: list, metadata: list[dict]):
    """Add embeddings + their metadata to the FAISS index."""
    vecs = np.array(embeddings, dtype="float32")
    
    # Normalize so that inner product = cosine similarity
    faiss.normalize_L2(vecs)
    
    dim = vecs.shape[1]
    
    # Load existing index or create a new one
    if os.path.exists(INDEX_PATH):
        index = faiss.read_index(INDEX_PATH)
        existing_meta = json.load(open(META_PATH, "r"))
    else:
        index = faiss.IndexFlatIP(dim)  # Inner Product (cosine after normalization)
        existing_meta = []
    
    index.add(vecs)
    existing_meta.extend(metadata)
    
    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "w") as f:
        json.dump(existing_meta, f)

def search(query_embedding: list, top_k: int = 5) -> list[tuple]:
    """Find the top-k most similar chunks for a query."""
    if not os.path.exists(INDEX_PATH):
        return []
    
    index = faiss.read_index(INDEX_PATH)
    meta  = json.load(open(META_PATH, "r"))
    
    q = np.array([query_embedding], dtype="float32")
    faiss.normalize_L2(q)
    
    scores, ids = index.search(q, top_k)
    
    results = []
    for j, i in enumerate(ids[0]):
        if i != -1:  # -1 means no result found
            results.append((meta[i], float(scores[0][j])))
    
    return results