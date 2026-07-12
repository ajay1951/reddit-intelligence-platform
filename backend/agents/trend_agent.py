import json
from sqlalchemy import text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession
from backend.agents.base import BaseAgent

class TrendAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="TrendAgent")

    async def analyze_trends(self, session: AsyncSession, topic: str) -> str:
        # We perform a rough keyword match in SQL to find related posts
        # and aggregate the 'technologies' array to see which tech is mentioned most
        sql = text("""
            SELECT unnest(technologies) as tech, count(*) as count
            FROM posts
            WHERE title ILIKE :topic OR content ILIKE :topic
            GROUP BY tech
            ORDER BY count DESC
            LIMIT 15;
        """).bindparams(bindparam("topic", f"%{topic}%"))
        
        result = await session.execute(sql)
        tech_counts = {row.tech: row.count for row in result}
        
        if not tech_counts:
            # Try comments if posts yield nothing
            sql_comments = text("""
                SELECT unnest(technologies) as tech, count(*) as count
                FROM comments
                WHERE content ILIKE :topic
                GROUP BY tech
                ORDER BY count DESC
                LIMIT 15;
            """).bindparams(bindparam("topic", f"%{topic}%"))
            result_comments = await session.execute(sql_comments)
            tech_counts = {row.tech: row.count for row in result_comments}
            
        if not tech_counts:
            return "No significant technology trends found for this topic."
            
        system_prompt = (
            "You are a Trend Analysis Agent. You are given a list of technologies and their mention frequency "
            "related to a specific topic on Reddit.\n"
            "Analyze these hard metrics. Which technologies are dominating? Are there any surprising challengers? "
            "Write a short, data-backed trend analysis paragraph."
        )
        
        user_prompt = f"Topic: {topic}\n\nTechnology Mentions Data:\n{json.dumps(tech_counts, indent=2)}"
        
        analysis = await self.call_llm(system_prompt, user_prompt)
        return analysis
