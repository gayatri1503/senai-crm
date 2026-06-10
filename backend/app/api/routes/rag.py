from fastapi import APIRouter, Query
from app.rag.pipeline import search_knowledge_base

router = APIRouter()


@router.get("/rag/search")
async def rag_search(
    q: str = Query(..., description="Search query for the knowledge base"),
    top_k: int = Query(3, ge=1, le=10, description="Number of chunks to return")
):
    """
    Debug endpoint — query the RAG knowledge base and return
    retrieved chunks with similarity scores.
    """
    if not q.strip():
        return {
            "query": q,
            "results": [],
            "total_chunks_searched": 0
        }

    results = search_knowledge_base(q, top_k=top_k)

    return {
        "query": q,
        "results": [
            {
                "rank": i + 1,
                "source_doc": r["source_doc"],
                "similarity_score": r["similarity_score"],
                "chunk_index": r["chunk_index"],
                "text": r["text"],
            }
            for i, r in enumerate(results)
        ],
        "total_chunks_searched": top_k
    }