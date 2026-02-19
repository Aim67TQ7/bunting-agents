"""
Agent 2: Risk Analysis and Clause Comparison
This agent analyzes buyer documents for contradictions with seller baseline terms.
"""

import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from app import LLMClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Agent2Risk:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.llm = LLMClient(model=model, temperature=0.7)
    
    def load_seller_baseline(self) -> str:
        """Load seller baseline terms."""
        try:
            with open("seller.md", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("seller.md not found, using default baseline")
            return "Standard seller terms and conditions apply."
    
    def analyze_risks(self, agent1_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze buyer document for contradictions with seller baseline.
        Focus only on direct conflicts, not missing terms.
        """
        try:
            contract_text = agent1_data["contract_text"]
            metadata = agent1_data["metadata"]
            seller_terms = self.load_seller_baseline()
            
            # Risk analysis prompt focusing on contradictions only
            risk_prompt = """You are analyzing buyer contract terms for CONTRADICTIONS with seller baseline terms.

CRITICAL RULES:
- Only flag DIRECT CONFLICTS between buyer and seller terms
- Ignore missing/silent terms (they favor seller)
- Focus on contradictions that create liability or financial risk
- Rate severity: LOW (minor variance), MEDIUM (moderate risk), HIGH (major liability)

Return JSON:
{{
  "risk_summary": "Brief overview of main contradictions found",
  "clause_diffs": [{{
    "clause": "Name of conflicting clause/topic",
    "contradiction": "Direct statement of what conflicts between buyer and seller terms", 
    "severity": "LOW/MEDIUM/HIGH",
    "score_delta": -5
  }}],
  "total_risk_score": 0
}}

SELLER BASELINE TERMS:
---
{seller_terms}
---

BUYER CONTRACT TEXT:
---
{contract_text}
---"""
            
            # Use first 4000 characters for analysis
            fit_text = contract_text[:4000] if len(contract_text) > 4000 else contract_text
            
            analysis = self.llm.json_response(
                "Analyze buyer contract for contradictions with seller baseline. Focus only on direct conflicts.",
                risk_prompt.format(seller_terms=seller_terms, contract_text=fit_text),
                max_output_tokens=2000
            )
            
            # Calculate compliance score
            clause_diffs = analysis.get("clause_diffs", [])
            total_delta = sum(diff.get("score_delta", 0) for diff in clause_diffs)
            compliance_score = max(0.0, min(100.0, 100.0 + total_delta))
            
            # Create output for next agent
            output = {
                "agent": "risk_analyzer", 
                "timestamp": datetime.utcnow().isoformat(),
                "file_path": agent1_data["file_path"],
                "metadata": metadata,
                "risk_analysis": analysis,
                "compliance_score": compliance_score,
                "clause_diffs": clause_diffs,
                "risk_summary": analysis.get("risk_summary", "Risk analysis completed"),
                "next_agent": "agent3_report"
            }
            
            # Save intermediate result
            output_file = f"agent2_output_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            output_path = os.path.join("reports", output_file)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, default=str)
            
            logger.info(f"Agent 2 completed. Found {len(clause_diffs)} contradictions. Score: {compliance_score}")
            return output
            
        except Exception as e:
            logger.error(f"Agent 2 risk analysis failed: {e}")
            raise


def run_agent2(agent1_data: Dict[str, Any]) -> str:
    """Run Agent 2 and trigger Agent 3."""
    agent = Agent2Risk()
    result = agent.analyze_risks(agent1_data)
    
    # Trigger final agent
    from agent3_report import run_agent3
    return run_agent3(result)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            agent1_data = json.load(f)
        output_path = run_agent2(agent1_data)
        print(f"Final output: {output_path}")