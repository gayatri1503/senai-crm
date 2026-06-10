from app.rag.pipeline import search_knowledge_base

tests = [
    "refund request cancel subscription",
    "ransomware security threat escalation",
    "GDPR data portability request",
    "SLA breach credit calculation",
    "HIPAA compliance BAA healthcare",
]

for query in tests:
    results = search_knowledge_base(query, top_k=1)
    if results:
        r = results[0]
        print(f"Query: {query}")
        print(f"  -> [{r['source_doc']}] score={r['similarity_score']}")
        print(f"  -> {r['text'][:120]}")
        print()