"""
Agent 3: Final Report Generation and Scoring
This agent creates the final comprehensive report with all formats.
"""

import os
import json
import logging
from typing import Dict, Any, Tuple
from datetime import datetime
from app import AnalysisResult, PartyInfo, LineItem, ClauseDiff

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Agent3Report:
    def __init__(self):
        pass
    
    def generate_final_report(self, agent_data: Dict[str, Any]) -> AnalysisResult:
        """
        Generate final structured report from agent analysis data.
        """
        try:
            # Extract data from previous agents
            metadata = agent_data.get("metadata", {})
            file_path = agent_data.get("file_path", "")
            
            # Handle seller documents vs buyer risk analysis
            if agent_data.get("agent") == "parser" and agent_data.get("is_seller_document"):
                # Seller document - no risk analysis needed
                compliance_score = 100.0
                clause_diffs = []
                risk_summary = "Seller document - no contradictions to analyze"
                brief_summary = "Bunting seller document processed successfully"
            else:
                # Buyer document with risk analysis
                risk_analysis = agent_data.get("risk_analysis", {})
                compliance_score = agent_data.get("compliance_score", 0.0)
                clause_diffs = agent_data.get("clause_diffs", [])
                risk_summary = agent_data.get("risk_summary", "Analysis completed")
                brief_summary = f"Found {len(clause_diffs)} contradictions. Compliance: {compliance_score:.1f}%"
            
            # Build party info
            parties_data = metadata.get("parties", {})
            parties = PartyInfo(
                customer_name=parties_data.get("customer_name"),
                address_line=parties_data.get("address_line"),
                city=parties_data.get("city"),
                state=parties_data.get("state"),
                phone=parties_data.get("phone"),
                email=parties_data.get("email")
            )
            
            # Build line items
            line_items = []
            for item_data in metadata.get("line_items", []):
                if item_data:  # Skip empty items
                    line_items.append(LineItem(
                        part_number=item_data.get("part_number"),
                        description=item_data.get("description"),
                        quantity=item_data.get("quantity"),
                        unit_price=item_data.get("unit_price"),
                        currency=item_data.get("currency"),
                        extended_price=item_data.get("extended_price")
                    ))
            
            # Build clause differences
            clause_differences = []
            for diff_data in clause_diffs:
                if diff_data:  # Skip empty diffs
                    clause_differences.append(ClauseDiff(
                        clause=diff_data.get("clause", "Unknown"),
                        contradiction=diff_data.get("contradiction", "Conflict detected"),
                        severity=diff_data.get("severity", "MEDIUM"),
                        score_delta=float(diff_data.get("score_delta", 0))
                    ))
            
            # Create final analysis result
            result = AnalysisResult(
                document_type=metadata.get("document_type", "CONTRACT"),
                risk_summary=risk_summary,
                parties=parties,
                buyer_reference_numbers=metadata.get("buyer_reference_numbers", []),
                effective_date=metadata.get("effective_date"),
                expiry_date=metadata.get("expiry_date"),
                payment_terms=metadata.get("payment_terms"),
                line_items=line_items,
                clause_diffs=clause_differences,
                compliance_score=compliance_score,
                brief_summary=brief_summary
            )
            
            logger.info(f"Agent 3 completed final report generation")
            return result
            
        except Exception as e:
            logger.error(f"Agent 3 report generation failed: {e}")
            raise
    
    def write_reports(self, result: AnalysisResult, contract_path: str) -> Tuple[str, str, str]:
        """Write JSON, Markdown, and XML reports."""
        os.makedirs("reports", exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        json_path = os.path.join("reports", f"t3rms_report_{ts}.json")
        md_path = os.path.join("reports", f"t3rms_report_{ts}.md")
        xml_path = os.path.join("reports", f"t3rms_report_{ts}.xml")
        
        # Write JSON report
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result.dict(), f, indent=2, default=str)
        
        # Write Markdown report
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {result.document_type or 'CONTRACT'} Analysis Report\\n\\n")
            f.write(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\\n")
            f.write(f"**Document:** {os.path.basename(contract_path)}\\n\\n")
            
            f.write(f"## Compliance Score: {result.compliance_score:.1f}/100\\n\\n")
            
            if result.risk_summary:
                f.write(f"## Risk Summary\\n\\n{result.risk_summary}\\n\\n")
            
            f.write(f"## Analysis Summary\\n\\n{result.brief_summary}\\n\\n")
            
            # Contradictions with color coding
            if result.clause_diffs:
                f.write(f"## Contradictions Found\\n\\n")
                for diff in result.clause_diffs:
                    severity_color = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(diff.severity, "⚪")
                    f.write(f"### {severity_color} {diff.clause}\\n\\n")
                    f.write(f"**Severity:** {diff.severity}\\n")
                    f.write(f"**Impact:** {diff.score_delta:+.1f}\\n")
                    f.write(f"**Contradiction:** {diff.contradiction}\\n\\n")
            
            # Line items
            if result.line_items:
                f.write(f"## Line Items\\n\\n")
                for item in result.line_items:
                    f.write(f"- **{item.part_number or 'N/A'}**: {item.description or 'N/A'}")
                    if item.quantity:
                        f.write(f" (Qty: {item.quantity})")
                    if item.unit_price:
                        f.write(f" @ {item.currency or '$'}{item.unit_price}")
                    f.write("\\n")
        
        # Write XML report (simplified)
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\\n')
            f.write('<analysis_report>\\n')
            f.write(f'  <compliance_score>{result.compliance_score:.1f}</compliance_score>\\n')
            f.write(f'  <document_type>{result.document_type or "CONTRACT"}</document_type>\\n')
            f.write(f'  <brief_summary><![CDATA[{result.brief_summary}]]></brief_summary>\\n')
            
            if result.clause_diffs:
                f.write('  <contradictions>\\n')
                for diff in result.clause_diffs:
                    f.write('    <contradiction>\\n')
                    f.write(f'      <clause><![CDATA[{diff.clause}]]></clause>\\n')
                    f.write(f'      <severity>{diff.severity}</severity>\\n')
                    f.write(f'      <score_delta>{diff.score_delta}</score_delta>\\n')
                    f.write(f'      <description><![CDATA[{diff.contradiction}]]></description>\\n')
                    f.write('    </contradiction>\\n')
                f.write('  </contradictions>\\n')
            
            f.write('</analysis_report>\\n')
        
        return json_path, md_path, xml_path


def run_agent3(agent_data: Dict[str, Any]) -> str:
    """Run Agent 3 and generate final reports."""
    agent = Agent3Report()
    
    # Generate final analysis result
    result = agent.generate_final_report(agent_data)
    
    # Write all report formats
    contract_path = agent_data.get("file_path", "document")
    json_path, md_path, xml_path = agent.write_reports(result, contract_path)
    
    logger.info(f"All reports generated: JSON={json_path}, MD={md_path}, XML={xml_path}")
    
    # Return the JSON path as the main output
    return json_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            agent_data = json.load(f)
        output_path = run_agent3(agent_data)
        print(f"Final reports generated: {output_path}")