from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.models.models import Comment, Post
from backend.repositories.chroma_repository import ChromaRepository
from backend.services.embedding_service import EmbeddingService


class SemanticService:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        chroma_repository: ChromaRepository | None = None,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.chroma_repository = chroma_repository or ChromaRepository()

    async def index_documents(self, session: AsyncSession) -> int:
        posts_result = await session.execute(
            select(Post).options(joinedload(Post.subreddit))
        )
        posts = posts_result.scalars().all()

        comments_result = await session.execute(
            select(Comment).options(joinedload(Comment.post).joinedload(Post.subreddit))
        )
        comments = comments_result.scalars().all()

        documents: list[str] = []
        metadatas: list[dict[str, str | int | None]] = []
        ids: list[str] = []

        for post in posts:
            body = "\\n".join(filter(None, [post.title, post.content]))
            if not body:
                continue
            ids.append(f"post-{post.id}")
            documents.append(body)
            metadatas.append(
                {
                    "type": "post",
                    "subreddit": post.subreddit.name if post.subreddit else None,
                    "url": post.url,
                    "post_id": post.id,
                }
            )

        for comment in comments:
            if not comment.content:
                continue
            ids.append(f"comment-{comment.id}")
            documents.append(comment.content)
            metadatas.append(
                {
                    "type": "comment",
                    "subreddit": comment.post.subreddit.name if comment.post and comment.post.subreddit else None,
                    "url": comment.post.url if comment.post else None,
                    "comment_id": comment.id,
                }
            )

        if not documents:
            return 0

        embeddings = await self.embedding_service.generate_embeddings(documents)
        self.chroma_repository.add_documents(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return len(ids)

    async def semantic_search(self, query: str, top_k: int = 5) -> list[dict[str, str | int | None]]:
        embedding = await self.embedding_service.generate_embedding(query)
        result = self.chroma_repository.query(embedding=embedding, n_results=top_k)

        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        distances = result.get("distances", [])

        hits: list[dict[str, str | int | None]] = []
        for index, document in enumerate(documents[0] if documents else []):
            hits.append(
                {
                    "id": result["ids"][0][index] if result.get("ids") else f"hit-{index}",
                    "document": document,
                    "metadata": metadatas[0][index] if metadatas else {},
                    "distance": distances[0][index] if distances else None,
                }
            )

        return hits

    async def keyword_search(self, session: AsyncSession, query: str, top_k: int = 5) -> list[dict[str, str | int | None]]:
        from backend.repositories.post_repository import PostRepository
        from backend.repositories.comment_repository import CommentRepository
        
        post_repo = PostRepository()
        comment_repo = CommentRepository()
        
        posts = await post_repo.search_posts(session, query, limit=top_k)
        comments = await comment_repo.search_comments(session, query, limit=top_k)
        
        hits: list[dict[str, str | int | None]] = []
        for post in posts:
            hits.append({
                "id": f"post-{post.id}",
                "document": f"{post.title}\\n{post.content}",
                "metadata": {"type": "post", "url": post.url, "subreddit": post.subreddit.name if post.subreddit else None},
                "score": 1.0
            })
            
        for comment in comments:
            hits.append({
                "id": f"comment-{comment.id}",
                "document": comment.content,
                "metadata": {"type": "comment", "url": comment.post.url if comment.post else None, "subreddit": comment.post.subreddit.name if comment.post and comment.post.subreddit else None},
                "score": 1.0
            })
            
        return hits[:top_k]

    def rrf_merge(self, dense_results: list[dict], sparse_results: list[dict], k: int = 60, top_k: int = 5) -> list[dict]:
        rrf_scores = {}
        docs = {}
        
        for rank, hit in enumerate(dense_results):
            doc_id = hit["id"]
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
                docs[doc_id] = hit
            rrf_scores[doc_id] += 1.0 / (k + rank + 1)
            
        for rank, hit in enumerate(sparse_results):
            doc_id = hit["id"]
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
                docs[doc_id] = hit
            rrf_scores[doc_id] += 1.0 / (k + rank + 1)
            
        sorted_hits = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        merged = []
        for doc_id, score in sorted_hits[:top_k]:
            hit = docs[doc_id].copy()
            hit["rrf_score"] = score
            merged.append(hit)
            
        return merged

    async def hybrid_search(self, session: AsyncSession, query: str, top_k: int = 5) -> list[dict[str, str | int | None]]:
        dense_hits = await self.semantic_search(query, top_k=top_k * 2)
        sparse_hits = await self.keyword_search(session, query, top_k=top_k * 2)
        
        return self.rrf_merge(dense_hits, sparse_hits, top_k=top_k)
