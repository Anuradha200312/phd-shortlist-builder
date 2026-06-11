from __future__ import annotations
import json
import re
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import chain
from llm.providers import build_llm_chain

FEEDBACK_ANALYSIS_PROMPT = PromptTemplate.from_template("""
Analyze the following PhD application outcome data and identify patterns:

Outcomes (sample):
{outcomes_sample}

Area success rates:
{area_rates}

Institution response rates:
{institution_rates}

Provide structured insights:
1. Which research areas have highest ADMIT/INTERVIEW rates?
2. Which institutions are most responsive?
3. What supervisor characteristics predict positive outcomes?
4. Recommended adjustments to future shortlist scoring weights?

Return ONLY a valid JSON object matching the following structure. Do NOT include any markdown formatting, code blocks (such as ```json or ```python), or explanatory text. Output ONLY the JSON.

Expected JSON Structure:
{{
  "area_adjustments": {{
    "area_name": adjustment_value
  }},
  "institution_boosts": {{
    "institution_name": boost_value
  }},
  "scoring_recommendations": {{
    "weight_name": "recommendation description"
  }}
}}
""")

@chain
def robust_json_parser(output) -> dict:
    """Robust parser that extracts JSON from the LLM output, handling markdown blocks or Python snippets."""
    # Handle message objects
    output_text = getattr(output, "content", str(output))
    
    # Try parsing clean JSON
    try:
        return json.loads(output_text.strip())
    except Exception:
        pass

    # Try searching for ```json block
    match = re.search(r'```json\s*(.*?)\s*```', output_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # Try searching for ```python or any block
    match = re.search(r'```(?:python|)\s*(.*?)\s*```', output_text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        # Look for any JSON-like dict inside python script
        dict_match = re.search(r'(\{.*\})', content, re.DOTALL)
        if dict_match:
            try:
                return json.loads(dict_match.group(1).strip())
            except Exception:
                pass

    # Try searching for any {...} in the entire text
    match = re.search(r'(\{.*\})', output_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # Fallback structure if parsing fails completely
    return {
        "area_adjustments": {},
        "institution_boosts": {},
        "scoring_recommendations": {"llm_output_parsing_failed": output_text[:500]}
    }


feedback_analysis_chain = (
    FEEDBACK_ANALYSIS_PROMPT
    | build_llm_chain()
    | robust_json_parser
)
