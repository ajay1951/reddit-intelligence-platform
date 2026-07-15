from __future__ import annotations

from chromadb import Client
from chromadb.config import Settings as ChromaSettings

from backend.config import settings


class ChromaRepository:
    def __init__(self) -> None:
        settings_kwargs = {
            "persist_directory": settings.chroma_persist_directory,
            "is_persistent": True,
        }
        self.client = Client(
            settings=ChromaSettings(**settings_kwargs),
            tenant=settings.chroma_tenant,
            database=settings.chroma_database,
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"source": "backend"},
        )

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, str | int | None]],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        kwargs = {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
        }
        if embeddings is not None:
            kwargs["embeddings"] = embeddings
            
        self.collection.add(**kwargs)

    def query(
        self,
        n_results: int = 5,
        embedding: list[float] | None = None,
        query_text: str | None = None,
    ) -> dict[str, list]:
        kwargs = {
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if embedding is not None:
            kwargs["query_embeddings"] = [embedding]
        if query_text is not None:
            kwargs["query_texts"] = [query_text]
        return self.collection.query(**kwargs)

    def delete_documents(self, ids: list[str]) -> None:
        if ids:
            self.collection.delete(ids=ids)

    def reset_collection(self) -> None:
        self.collection.delete()
