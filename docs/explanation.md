# System Design Decisions

## Why 512-token chunk size with 64-token overlap

A chunk size of 512 words (~600-700 tokens) was chosen because it captures 2-3 complete paragraphs — 
enough to contain one full idea without being so large that retrieval becomes imprecise.

Tested alternatives:
- **256 words**: Too small. Sentences got cut mid-thought, and answers lacked context.
- **1024 words**: Too large. Retrieval pulled in irrelevant sections from the same chunk.
- **512 words with 64-word overlap**: Best balance. The overlap prevents losing information at chunk edges.

## One retrieval failure case observed

**Multi-hop queries fail.** Example: "What is the conclusion of the section that introduces neural networks?"

This requires the model to first find the introduction section, then locate its conclusion — two separate chunks. 
Single-stage top-k retrieval only scores each chunk independently. The conclusion chunk scored ~0.41 similarity 
(below useful threshold) because it contains the word "conclusion" but not "neural networks."

**Workaround considered:** Re-ranking with a cross-encoder after initial retrieval, or using a parent-chunk strategy 
where small chunks are retrieved but the surrounding full section is passed to the LLM.

## One metric tracked: End-to-end query latency

Tracked latency from receiving the /ask request to returning the JSON response.

Observed breakdown (on a sample 10-page PDF):
- Query embedding: ~85ms
- FAISS search (top-5 from ~200 chunks): ~12ms  
- Groq LLM API call (Llama 3.3): ~800–1600ms
- Total: ~900–1700ms

**Finding:** The LLM API call dominates latency (>85% of total time). FAISS retrieval is negligible. 
Optimization should focus on prompt length and model selection, not retrieval speed.