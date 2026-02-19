"""
Agent 1: Document Parsing and Metadata Extraction
This agent handles initial document processing and extracts basic metadata.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app import LLMClient, extract_text_from_file, is_bunting_document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Agent1Parser:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.llm = LLMClient(model=model, temperature=0.3)
    
    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text and basic metadata from document.
        Returns structured data for next agent.
        """
        try:
            # Extract text from document
            contract_text = extract_text_from_file(file_path)
            logger.info(f"Extracted {len(contract_text)} characters from document")
            
            # Determine document type and source
            is_seller_doc = is_bunting_document(contract_text)
            doc_type = "SELLER_DOCUMENT" if is_seller_doc else "BUYER_DOCUMENT"
            
            # Extract basic metadata using LLM
            metadata_prompt = """Extract basic metadata from this document. Return JSON:
{
  "document_type": "CONTRACT/PO/QUOTE/SELLER_DOCUMENT",
  "parties": {
    "customer_name": "string or null",
    "address_line": "string or null", 
    "city": "string or null",
    "state": "string or null",
    "phone": "string or null",
    "email": "string or null"
  },
  "buyer_reference_numbers": ["list of PO numbers, quote numbers, etc"],
  "effective_date": "YYYY-MM-DD or null",
  "expiry_date": "YYYY-MM-DD or null",
  "payment_terms": "string or null",
  "line_items": [{
    "part_number": "string or null",
    "description": "string or null",
    "quantity": "number or null",
    "unit_price": "number or null",
    "currency": "USD/EUR/etc",
    "extended_price": "number or null"
  }]
}"""
            
            # Use first 3000 characters for metadata extraction
            fit_text = contract_text[:3000] if len(contract_text) > 3000 else contract_text
            metadata = self.llm.json_response(metadata_prompt, f"Document text:\n{fit_text}", max_output_tokens=1500)
            
            # Ensure document type is set correctly
            metadata["document_type"] = doc_type
            
            # Create output for next agent
            output = {
                "agent": "parser",
                "timestamp": datetime.utcnow().isoformat(),
                "file_path": file_path,
                "text_length": len(contract_text),
                "contract_text": contract_text,
                "metadata": metadata,
                "is_seller_document": is_seller_doc,
                "next_agent": "agent2_risk" if not is_seller_doc else "agent3_report"
            }
            
            # Save intermediate result
            output_file = f"agent1_output_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            output_path = os.path.join("reports", output_file)
            os.makedirs("reports", exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, default=str)
            
            logger.info(f"Agent 1 completed. Output saved to {output_path}")
            return output
            
        except Exception as e:
            logger.error(f"Agent 1 parsing failed: {e}")
            raise


def run_agent1(file_path: str) -> str:
    """Run Agent 1 and return path to output file for next agent."""
    agent = Agent1Parser()
    result = agent.parse_document(file_path)
    
    # Trigger next agent
    if result["next_agent"] == "agent2_risk":
        from agent2_risk import run_agent2
        return run_agent2(result)
    else:
        from agent3_report import run_agent3
        return run_agent3(result)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        output_path = run_agent1(file_path)
        print(f"Final output: {output_path}")