from backend.agents.base import BaseAgent

class ReportAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="ReportAgent")

    async def generate_report(self, topic: str, research_data: str, trend_data: str, sentiment_data: str) -> str:
        system_prompt = (
            "You are a Lead Intelligence Analyst (Report Agent) similar to an analyst at Palantir or Gartner.\n"
            "Your objective is to synthesize raw intelligence gathered by your sub-agents into a cohesive, "
            "executive-level Market Intelligence Briefing.\n\n"
            "Format the report using Markdown with the following sections:\n"
            "1. **Executive Summary**: High-level overview of the topic.\n"
            "2. **Key Findings**: 3-5 bullet points derived from the Research Agent.\n"
            "3. **Technology & Trend Radar**: Insights from the Trend Agent.\n"
            "4. **Public Perception**: Sentiment analysis from the Sentiment Agent.\n"
            "5. **Strategic Recommendations**: What should an enterprise do based on this data?\n\n"
            "Maintain a highly professional, objective, and analytical tone. Do not invent data."
        )
        
        user_prompt = f"""
Topic: {topic}

=== RESEARCH AGENT FINDINGS ===
{research_data}

=== TREND AGENT FINDINGS ===
{trend_data}

=== SENTIMENT AGENT FINDINGS ===
{sentiment_data}
"""
        
        report = await self.call_llm(system_prompt, user_prompt)
        return report
