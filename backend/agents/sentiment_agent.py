import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.agents.base import BaseAgent

class SentimentAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="SentimentAgent")

    async def analyze_sentiment(self, session: AsyncSession, topic: str) -> str:
        # Aggregate sentiment labels for the topic
        sql = """
            SELECT sentiment_label, count(*) as count
            FROM comments
            WHERE content ILIKE :topic AND sentiment_label IS NOT NULL
            GROUP BY sentiment_label;
        """
        result = await session.execute(text(sql), {"topic": f"%{topic}%"})
        sentiment_counts = {row.sentiment_label: row.count for row in result}
        
        if not sentiment_counts:
            return "No sentiment data available for this topic."
            
        system_prompt = (
            "You are a Sentiment Analysis Agent. You are given an aggregated sentiment count (Positive, Neutral, Negative) "
            "for a specific topic being discussed on Reddit.\n"
            "Analyze the overall public perception. Is it overwhelmingly positive? Highly controversial? "
            "Write a brief, objective summary of the market sentiment."
        )
        
        user_prompt = f"Topic: {topic}\n\nSentiment Data:\n{json.dumps(sentiment_counts, indent=2)}"
        
        analysis = await self.call_llm(system_prompt, user_prompt)
        return analysis
