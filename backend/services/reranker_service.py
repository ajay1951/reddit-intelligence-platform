from sentence_transformers import CrossEncoder

class RerankerService:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        # BAAI/bge-reranker-base is a strong cross-encoder for reranking
        self.model = CrossEncoder(model_name, max_length=512)

    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        """
        Re-ranks a list of documents based on a query using a Cross-Encoder.
        documents should be a list of dictionaries, each containing a 'document' key.
        """
        if not documents:
            return []

        # Prepare pairs of (query, document_text)
        pairs = [[query, doc["document"]] for doc in documents]
        
        # Predict scores
        scores = self.model.predict(pairs)
        
        # Add scores to documents and sort
        for i, doc in enumerate(documents):
            doc["rerank_score"] = float(scores[i])
            
        ranked_docs = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
        return ranked_docs[:top_k]
