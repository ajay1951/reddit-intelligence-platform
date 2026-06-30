from sqlalchemy.ext.asyncio import AsyncSession
from backend.agents.base import BaseAgent
from backend.services.rag_service import RagService

class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="ResearchAgent")
        self.rag_service = RagService()

    async def gather_intelligence(self, session: AsyncSession, topic: str) -> str:
        system_prompt = (
            "You are an expert Research Agent gathering intelligence from a Market Intelligence Platform.\n"
            "Your goal is to extract the most critical insights, facts, and observations about the provided topic.\n"
            "You will be given raw search results from Reddit discussions. Summarize the key findings, pain points, "
            "and adoption trends mentioned in the text. Be concise, highly analytical, and objective."
        )
        
        # We fetch top 10 results via Hybrid RAG
        candidate_sources = await self.rag_service.semantic_service.hybrid_search(session, topic, top_k=20)
        sources = self.rag_service.reranker_service.rerank(topic, candidate_sources, top_k=10)
        
        if not sources:
            return "No relevant discussions found in the database."
            
        context_lines = []
        for src in sources:
            context_lines.append(f"--- Document ({src['metadata'].get('type')}) ---")
            context_lines.append(src["document"])
            
        user_prompt = f"Topic: {topic}\n\nSearch Results:\n" + "\n".join(context_lines)
        
        findings = await self.call_llm(system_prompt, user_prompt)
        return findings
