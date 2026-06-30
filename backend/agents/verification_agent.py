from backend.agents.base import BaseAgent

class VerificationAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="VerificationAgent")

    async def verify_claims(self, topic: str, drafted_report: str) -> str:
        system_prompt = (
            "You are a strict Verification and Fact-Checking Agent.\n"
            "Your job is to review a drafted intelligence report for a given topic.\n"
            "Look for any claims that sound hallucinated, overly confident without data, "
            "or excessively vague. Provide a 'Confidence Score' out of 100, and a list of "
            "warnings or verifications. If the report looks solid and based on the data provided by previous agents, say so."
        )
        
        user_prompt = f"Topic: {topic}\n\nDrafted Report:\n{drafted_report}"
        
        verification_result = await self.call_llm(system_prompt, user_prompt)
        return verification_result
