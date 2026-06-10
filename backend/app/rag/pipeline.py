import os
import re
from pathlib import Path
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# --- Config ---
KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent.parent / "knowledge_base"
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = "senai_knowledge_base"
CHUNK_SIZE = 400        # target tokens per chunk
CHUNK_OVERLAP = 50      # overlap between chunks
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # same family as MHT CET project


# --- Singleton clients ---
_chroma_client = None
_embedding_model = None
_collection = None


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return _chroma_client


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def get_collection():
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


# --- Chunking ---

def chunk_document(text: str, source_doc: str) -> List[Dict]:
    """
    Split document into chunks by ## headings first,
    then by size if a section is too large.
    This keeps each policy section as its own retrievable unit.
    """
    # Split on ## headings (keep the heading with its content)
    sections = re.split(r'(?=^## )', text, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    chunks = []
    chunk_index = 0

    for section in sections:
        words = section.split()

        # If section fits in one chunk, keep it whole
        if len(words) <= CHUNK_SIZE:
            chunks.append({
                "id": f"{source_doc}_chunk_{chunk_index}",
                "text": section,
                "source_doc": source_doc,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

        # Otherwise split by paragraphs with overlap
        else:
            paragraphs = [p.strip() for p in re.split(r'\n\n+', section) if p.strip()]
            current_chunk = []
            current_length = 0

            for para in paragraphs:
                para_length = len(para.split())
                if current_length + para_length > CHUNK_SIZE and current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append({
                        "id": f"{source_doc}_chunk_{chunk_index}",
                        "text": chunk_text,
                        "source_doc": source_doc,
                        "chunk_index": chunk_index,
                    })
                    chunk_index += 1
                    # Overlap: keep last paragraph
                    current_chunk = [current_chunk[-1]]
                    current_length = len(current_chunk[0].split())
                current_chunk.append(para)
                current_length += para_length

            if current_chunk:
                chunks.append({
                    "id": f"{source_doc}_chunk_{chunk_index}",
                    "text": "\n\n".join(current_chunk),
                    "source_doc": source_doc,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1

    return chunks


# --- Embedding and indexing ---

def embed_knowledge_base():
    """
    Load all 6 .md files, chunk them, embed, and store in ChromaDB.
    Call this once to seed the knowledge base.
    """
    model = get_embedding_model()
    collection = get_collection()

    # Clear existing data for fresh re-seed
    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        print(f"Cleared {len(existing['ids'])} existing chunks")

    md_files = list(KNOWLEDGE_BASE_DIR.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {KNOWLEDGE_BASE_DIR}")
        return

    total_chunks = 0

    for md_file in md_files:
        source_doc = md_file.name
        text = md_file.read_text(encoding="utf-8")

        chunks = chunk_document(text, source_doc)
        print(f"  {source_doc}: {len(chunks)} chunks")

        # Embed all chunks from this document
        texts = [c["text"] for c in chunks]
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            ids=[c["id"] for c in chunks],
            documents=texts,
            embeddings=embeddings,
            metadatas=[{
                "source_doc": c["source_doc"],
                "chunk_index": c["chunk_index"]
            } for c in chunks]
        )

        total_chunks += len(chunks)

    print(f"\nTotal chunks embedded: {total_chunks}")
    print(f"Collection size: {collection.count()}")


# --- Retrieval ---

def search_knowledge_base(query: str, top_k: int = 3) -> List[Dict]:
    """
    Search the knowledge base for relevant chunks.
    Returns top_k chunks with similarity scores.
    Used by both the LLM classifier and the agent.
    """
    model = get_embedding_model()
    collection = get_collection()

    if collection.count() == 0:
        return []

    query_embedding = model.encode([query]).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        similarity = 1 - distance   # cosine distance → similarity

        chunks.append({
            "chunk_id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "source_doc": results["metadatas"][0][i]["source_doc"],
            "chunk_index": results["metadatas"][0][i]["chunk_index"],
            "similarity_score": round(similarity, 4),
        })

    return chunks


if __name__ == "__main__":
    print("Seeding knowledge base...")
    embed_knowledge_base()
    print("\nTesting retrieval...")
    results = search_knowledge_base("non-profit discount pricing")
    for r in results:
        print(f"\n  [{r['source_doc']}] score={r['similarity_score']}")
        print(f"  {r['text'][:200]}...")