import asyncio
import structlog
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.research_agent import ResearchAgent
from backend.agents.trend_agent import TrendAgent
from backend.agents.sentiment_agent import SentimentAgent
from backend.agents.report_agent import ReportAgent
from backend.agents.verification_agent import VerificationAgent

logger = structlog.get_logger(__name__)

class DeepResearchCoordinator:
    def __init__(self):
        self.research_agent = ResearchAgent()
        self.trend_agent = TrendAgent()
        self.sentiment_agent = SentimentAgent()
        self.report_agent = ReportAgent()
        self.verification_agent = VerificationAgent()

    async def conduct_deep_research(self, session: AsyncSession, topic: str) -> AsyncGenerator[dict, None]:
        """
        Executes the multi-agent workflow and yields intermediate steps (chain of thought)
        so the frontend can display real-time progress.
        """
        yield {"step": "research", "status": "running", "message": f"Research Agent is querying vector database for '{topic}'..."}
        research_data = await self.research_agent.gather_intelligence(session, topic)
        yield {"step": "research", "status": "complete", "message": "Research gathered.", "data": research_data}

        yield {"step": "trends", "status": "running", "message": "Trend Agent is aggregating SQL metrics..."}
        trend_data = await self.trend_agent.analyze_trends(session, topic)
        yield {"step": "trends", "status": "complete", "message": "Trends analyzed.", "data": trend_data}

        yield {"step": "sentiment", "status": "running", "message": "Sentiment Agent is computing public perception..."}
        sentiment_data = await self.sentiment_agent.analyze_sentiment(session, topic)
        yield {"step": "sentiment", "status": "complete", "message": "Sentiment computed.", "data": sentiment_data}

        yield {"step": "report", "status": "running", "message": "Report Agent is synthesizing the executive briefing..."}
        report = await self.report_agent.generate_report(topic, research_data, trend_data, sentiment_data)
        yield {"step": "report", "status": "complete", "message": "Draft report generated.", "data": report}

        yield {"step": "verify", "status": "running", "message": "Verification Agent is cross-checking claims..."}
        verification = await self.verification_agent.verify_claims(topic, report)
        yield {"step": "verify", "status": "complete", "message": "Verification complete.", "data": verification}
        
        # Append verification to report
        final_report = f"{report}\n\n---\n### Agent Verification Status\n{verification}"
        
        yield {"step": "final", "status": "complete", "message": "Deep Research Workflow Complete.", "data": final_report}
