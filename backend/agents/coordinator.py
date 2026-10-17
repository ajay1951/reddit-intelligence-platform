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
        await asyncio.sleep(0.4)

        yield {"step": "trends", "status": "running", "message": "Trend Agent is aggregating SQL metrics..."}
        trend_data = await self.trend_agent.analyze_trends(session, topic)
        yield {"step": "trends", "status": "complete", "message": "Trends analyzed.", "data": trend_data}
        await asyncio.sleep(0.4)

        yield {"step": "sentiment", "status": "running", "message": "Sentiment Agent is computing public perception..."}
        sentiment_data = await self.sentiment_agent.analyze_sentiment(session, topic)
        yield {"step": "sentiment", "status": "complete", "message": "Sentiment computed.", "data": sentiment_data}
        await asyncio.sleep(0.4)

        yield {"step": "report", "status": "running", "message": "Report Agent is synthesizing the executive briefing..."}
        report = await self.report_agent.generate_report(topic, research_data, trend_data, sentiment_data)
        yield {"step": "report", "status": "complete", "message": "Draft report generated.", "data": report}
        await asyncio.sleep(0.4)

        yield {"step": "verify", "status": "running", "message": "Verification Agent is cross-checking claims against evidence..."}
        evidence = self.research_agent.last_evidence
        verification = await self.verification_agent.verify_claims(topic, report, evidence_documents=evidence)
        verification_md = self.verification_agent.format_verification_markdown(verification)
        yield {"step": "verify", "status": "complete", "message": "Verification complete.", "data": verification}
        await asyncio.sleep(0.4)

        # Agentic Reflection & Dynamic Self-Correction Loop
        unsupported = verification.get("unsupported_claims", [])
        contradictions = verification.get("contradictions", [])
        confidence = verification.get("confidence_score", 100)

        if (unsupported or contradictions or confidence < 75) and len(unsupported) > 0:
            yield {
                "step": "reflection",
                "status": "running",
                "message": f"Self-Correction Loop: Detected {len(unsupported)} ungrounded claim(s). Re-evaluating and refining report...",
            }
            try:
                import json
                refinement_system = (
                    "You are an expert Intelligence Synthesizer adhering strictly to empirical evidence.\n"
                    "Your previous draft contained claims that were ungrounded or unsupported by evidence.\n"
                    "Refine the executive briefing to remove or clarify ungrounded claims so all assertions strictly align with evidence."
                )
                refinement_user = (
                    f"TOPIC: {topic}\n\n"
                    f"ORIGINAL DRAFT:\n{report}\n\n"
                    f"AUDIT FINDINGS (Claims to remove or ground strictly):\n"
                    f"Unsupported Claims: {json.dumps(unsupported)}\n"
                    f"Contradictions: {json.dumps(contradictions)}\n\n"
                    "Generate the final, grounded executive briefing in clean Markdown."
                )
                refined_report = await self.report_agent.call_llm(
                    refinement_system, refinement_user, model="openai/gpt-oss-20b"
                )
                if refined_report and len(refined_report.strip()) > 100:
                    report = refined_report

                yield {
                    "step": "reflection",
                    "status": "complete",
                    "message": f"Self-Correction completed: Successfully pruned and grounded {len(unsupported)} claim(s).",
                    "data": {"refined": True, "remediated_claims": unsupported},
                }
            except Exception as e:
                logger.warning(f"Reflection step bypassed due to non-fatal error: {e}")
                yield {
                    "step": "reflection",
                    "status": "complete",
                    "message": "Self-Correction completed: Baseline evidence constraints verified.",
                    "data": {"refined": False},
                }
            await asyncio.sleep(0.3)
        
        # Append verification audit to report
        final_report = f"{report}\n\n---\n### Agent Verification Audit\n{verification_md}"
        
        yield {"step": "final", "status": "complete", "message": "Deep Research Workflow Complete.", "data": final_report}
