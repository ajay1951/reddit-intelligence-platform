import re
import json
from typing import Any
from backend.agents.base import BaseAgent


class VerificationAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="VerificationAgent")

    def cross_check_citations(
        self, drafted_report: str, evidence_documents: list[dict]
    ) -> dict[str, Any]:
        """
        Deterministically verifies that all citations and document references in the report
        exist within the retrieved evidence documents.
        """
        valid_ids: set[str] = set()
        valid_urls: set[str] = set()
        
        for doc in evidence_documents:
            if doc.get("id"):
                valid_ids.add(str(doc["id"]))
            meta = doc.get("metadata") or {}
            if meta.get("url"):
                valid_urls.add(str(meta["url"]).strip())

        # Match citations like [Source: url | ID: id] or [Source: id]
        explicit_citations = re.findall(r"\[Source:\s*([^\]]+)\]", drafted_report)
        id_mentions = set(re.findall(r"\b(post-\d+|comment-\d+)\b", drafted_report))

        valid_citations = []
        invalid_citations = []

        for cite in explicit_citations:
            parts = [p.strip() for p in cite.split("|")]
            found_valid = False
            for p in parts:
                cleaned = re.sub(r"^(?:url|id|source):\s*", "", p, flags=re.I).strip()
                if cleaned in valid_ids or cleaned in valid_urls:
                    found_valid = True
                    break
            if found_valid:
                valid_citations.append(cite)
            else:
                invalid_citations.append(cite)

        # Also check bare doc ID mentions
        for doc_id in id_mentions:
            if doc_id in valid_ids:
                if doc_id not in valid_citations:
                    valid_citations.append(doc_id)
            else:
                if doc_id not in invalid_citations:
                    invalid_citations.append(doc_id)

        total = len(valid_citations) + len(invalid_citations)
        validity_rate = (len(valid_citations) / total) if total > 0 else 1.0

        return {
            "total_citations": total,
            "valid_count": len(valid_citations),
            "invalid_count": len(invalid_citations),
            "valid_citations": valid_citations,
            "invalid_citations": invalid_citations,
            "validity_rate": round(validity_rate, 4),
        }

    async def verify_claims(
        self,
        topic: str,
        drafted_report: str,
        evidence_documents: list[dict] | None = None,
    ) -> dict[str, Any]:
        evidence = evidence_documents or []
        citation_audit = self.cross_check_citations(drafted_report, evidence)

        evidence_snippets = []
        for doc in evidence:
            doc_id = doc.get("id", "unknown")
            meta = doc.get("metadata") or {}
            url = meta.get("url", "")
            text = doc.get("document", "")
            evidence_snippets.append(f"<document id='{doc_id}' url='{url}'>\n{text}\n</document>")

        system_prompt = (
            "You are a strict Verification and Grounding Agent.\n"
            "Your job is to audit a drafted intelligence report against the retrieved Reddit evidence documents.\n"
            "Analyze whether every claim made in the report is directly supported by the evidence.\n"
            "Identify:\n"
            "1. Verified Claims (claims backed by the evidence)\n"
            "2. Unsupported Claims (hallucinations, unsourced extrapolations, or claims not present in evidence)\n"
            "3. Contradictions (statements that conflict with the evidence)\n\n"
            "Output your analysis in valid JSON format with keys:\n"
            "{\n"
            '  "confidence_score": <integer 0-100>,\n'
            '  "status": "<verified | partially_verified | unverified>",\n'
            '  "verified_claims": ["claim 1", ...],\n'
            '  "unsupported_claims": ["claim 1", ...],\n'
            '  "contradictions": ["item 1", ...],\n'
            '  "critique_summary": "<summary explanation>"\n'
            "}"
        )

        user_prompt = (
            f"Topic: {topic}\n\n"
            f"<retrieved_evidence>\n"
            + "\n".join(evidence_snippets)
            + f"\n</retrieved_evidence>\n\n"
            f"Drafted Report:\n{drafted_report}\n\n"
            "Audit the draft against the retrieved evidence and return valid JSON only."
        )

        raw_llm_response = await self.call_llm(system_prompt, user_prompt)
        
        # Parse JSON from LLM response safely
        parsed: dict[str, Any] = {}
        try:
            # Strip markdown code blocks if wrapped
            clean_json = raw_llm_response.strip()
            if clean_json.startswith("```"):
                clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
                clean_json = re.sub(r"\s*```$", "", clean_json)
            parsed = json.loads(clean_json)
        except Exception:
            # Fallback if LLM output was freeform text
            parsed = {
                "confidence_score": 75 if citation_audit["invalid_count"] == 0 else 40,
                "status": "partially_verified" if citation_audit["invalid_count"] == 0 else "unverified",
                "verified_claims": [],
                "unsupported_claims": citation_audit["invalid_citations"],
                "contradictions": [],
                "critique_summary": raw_llm_response,
            }

        # Merge deterministic citation check
        parsed["citation_audit"] = citation_audit
        
        # Penalize confidence score if citations are invalid or evidence is empty
        if not evidence:
            parsed["confidence_score"] = 0
            parsed["status"] = "unverified"
            parsed["critique_summary"] = "No evidence documents were retrieved to verify this report."
        elif citation_audit["invalid_count"] > 0:
            parsed["confidence_score"] = min(parsed.get("confidence_score", 100), 50)
            parsed["status"] = "partially_verified" if parsed.get("verified_claims") else "unverified"

        return parsed

    def format_verification_markdown(self, result: dict[str, Any]) -> str:
        """Converts structured verification dict into clean markdown report section."""
        score = result.get("confidence_score", 0)
        status = result.get("status", "unknown").upper()
        summary = result.get("critique_summary", "")
        verified = result.get("verified_claims", [])
        unsupported = result.get("unsupported_claims", [])
        citation_audit = result.get("citation_audit", {})

        md = [
            f"**Verification Status:** `{status}` | **Confidence Score:** `{score}/100`\n",
            f"**Audit Summary:** {summary}\n",
        ]

        if citation_audit.get("total_citations", 0) > 0:
            valid_c = citation_audit.get("valid_count", 0)
            total_c = citation_audit.get("total_citations", 0)
            md.append(f"**Citations Verified:** {valid_c}/{total_c} ({citation_audit.get('validity_rate', 0)*100:.1f}%)")
            if citation_audit.get("invalid_citations"):
                md.append(f"⚠️ **Invalid/Unresolved Citations:** {', '.join(citation_audit['invalid_citations'])}")

        if verified:
            md.append("\n**Verified Claims:**")
            for c in verified:
                md.append(f"- ✅ {c}")

        if unsupported:
            md.append("\n**Unsupported / Flagged Claims:**")
            for u in unsupported:
                md.append(f"- ⚠️ {u}")

        return "\n".join(md)

