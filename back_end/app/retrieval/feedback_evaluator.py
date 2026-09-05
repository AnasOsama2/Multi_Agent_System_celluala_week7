from typing import Dict, Any, Optional
from app.core.llm import llm_client
from app.core.logging import app_logger

class FeedbackEvaluator:
    """
    Evaluator model in the feedback loop.
    Compares the retrieved context and generated answer against the user's original query.
    Detects exact-match failures, semantic gaps, or incomplete answers, and provides
    reformulated search terms to trigger the self-correction branch.
    """
    def evaluate(
        self,
        query: str,
        context: str,
        answer: str,
        iteration: int = 1,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        # Cap iterations to avoid infinite loops
        if iteration > 2:
            return {
                "passed": True,
                "reason": "Max self-correction iterations reached",
                "reformulation": query
            }

        prompt = f"""
You are a RAG Evaluation and Feedback Agent.
Evaluate whether the retrieved context and generated answer accurately and completely answer the user query.

User Query: "{query}"

Retrieved Context:
\"\"\"
{context[:2500]}
\"\"\"

Generated Answer:
\"\"\"
{answer}
\"\"\"

Assess:
1. Exact Match & Entity Coverage: Does the context contain the specific entities, terms, error codes, or numbers requested?
2. Hallucination / Completeness: Is the answer fully supported by the retrieved context, or does it state that information is missing?

Respond in strict JSON:
{{
  "passed": true | false,
  "failure_type": "none" | "exact_match_missing" | "semantic_gap" | "incomplete_context",
  "reason": "short explanation of evaluation",
  "suggested_reformulation": "reformulated keyword-rich query for BM25 and vector search if failed"
}}
"""
        try:
            res = llm_client.generate_json(
                messages=[
                    {"role": "system", "content": "You are a strict retrieval quality evaluator. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                trace_id=trace_id
            )
            passed = bool(res.get("passed", True))
            app_logger.log_feedback_evaluation(passed, res, trace_id)
            return {
                "passed": passed,
                "failure_type": res.get("failure_type", "none"),
                "reason": res.get("reason", "Evaluation complete"),
                "reformulation": res.get("suggested_reformulation", query)
            }
        except Exception as e:
            app_logger.log_feedback_evaluation(True, {"error": str(e)}, trace_id)
            return {
                "passed": True,
                "reason": f"Evaluator fallback ({e})",
                "reformulation": query
            }


feedback_evaluator = FeedbackEvaluator()
