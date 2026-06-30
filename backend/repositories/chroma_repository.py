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
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, str | int | None]],
    ) -> None:
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query(
        self,
        embedding: list[float],
        n_results: int = 5,
    ) -> dict[str, list]:
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    def delete_documents(self, ids: list[str]) -> None:
        if ids:
            self.collection.delete(ids=ids)

    def reset_collection(self) -> None:
        self.collection.delete()
