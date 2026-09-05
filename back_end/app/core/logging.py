import logging
import sys
import json
import time
from typing import Any, Dict, Optional
from datetime import datetime
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Custom rich theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "critical": "bold white on red",
    "router": "bold magenta",
    "sql": "bold green",
    "retrieval": "bold blue",
    "eval": "bold yellow",
    "llm": "bold cyan"
})

console = Console(theme=custom_theme)

class StructuredLogger:
    """
    Centralized structured logger capturing every state transition, routing choice,
    SQL execution, similarity scores, reranker evaluations, feedback loop triggers, and LLM generation.
    """
    def __init__(self, name: str = "rag_system"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            # Rich console handler for beautiful interactive logs
            rich_handler = RichHandler(
                console=console,
                show_time=True,
                show_path=False,
                rich_tracebacks=True,
                markup=True
            )
            formatter = logging.Formatter(
                fmt="%(message)s",
                datefmt="[%Y-%m-%d %H:%M:%S]"
            )
            rich_handler.setFormatter(formatter)
            self.logger.addHandler(rich_handler)
            self.logger.propagate = False

    def log_state(
        self,
        event: str,
        step: str,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        level: str = "info"
    ):
        try:
            from datetime import timezone
            timestamp = datetime.now(timezone.utc).isoformat()
        except Exception:
            timestamp = datetime.now().isoformat()
        payload = {
            "timestamp": timestamp,
            "event": event,
            "step": step,
            "trace_id": trace_id or "global",
            "details": details or {}
        }
        
        formatted_details = json.dumps(details, default=str, indent=2) if details else ""
        msg = f"[bold cyan][{step.upper()}][/bold cyan] {event}"
        if formatted_details and formatted_details != "{}":
            msg += f"\n[dim]{formatted_details}[/dim]"

        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(msg)

    def log_routing(self, query: str, route: str, reasoning: str, trace_id: Optional[str] = None):
        self.log_state(
            event=f"Query routed to [bold magenta]{route}[/bold magenta]",
            step="router",
            details={"query": query, "route": route, "reasoning": reasoning},
            trace_id=trace_id
        )

    def log_sql_execution(self, query: str, sql: str, validation: str, row_count: int, trace_id: Optional[str] = None):
        self.log_state(
            event=f"SQL Executed ([green]{row_count} rows returned[/green])",
            step="sql_agent",
            details={"user_query": query, "generated_sql": sql, "validation": validation, "row_count": row_count},
            trace_id=trace_id
        )

    def log_retrieval(self, query: str, retrieved_count: int, top_scores: list, trace_id: Optional[str] = None):
        self.log_state(
            event=f"Retrieved {retrieved_count} candidate chunks",
            step="retriever",
            details={"query": query, "candidates": retrieved_count, "sample_scores": top_scores[:3]},
            trace_id=trace_id
        )

    def log_confidence(self, confidence_score: float, is_high_confidence: bool, action: str, trace_id: Optional[str] = None):
        status = "[green]HIGH CONFIDENCE[/green]" if is_high_confidence else "[yellow]LOW CONFIDENCE (Reranker Triggered)[/yellow]"
        self.log_state(
            event=f"Confidence Score: {confidence_score:.4f} -> {status}",
            step="confidence_check",
            details={"confidence_score": confidence_score, "is_high": is_high_confidence, "action": action},
            trace_id=trace_id
        )

    def log_rerank(self, reranked_count: int, top_scores: list, trace_id: Optional[str] = None):
        self.log_state(
            event=f"BAAI/bge-reranker-v2-m3 scored {reranked_count} candidates",
            step="reranker",
            details={"evaluated_count": reranked_count, "top_scores": top_scores[:3]},
            trace_id=trace_id
        )

    def log_feedback_evaluation(self, passed: bool, evaluation_details: Dict[str, Any], trace_id: Optional[str] = None):
        status = "[green]PASSED[/green]" if passed else "[bold red]FAILED (Self-Correction Loop Initiated)[/bold red]"
        self.log_state(
            event=f"Feedback Evaluation: {status}",
            step="feedback_evaluator",
            details=evaluation_details,
            trace_id=trace_id
        )

    def log_llm_response(self, prompt_tokens: int, completion_tokens: int, answer_snippet: str, trace_id: Optional[str] = None):
        self.log_state(
            event=f"LLM Generation Complete ({prompt_tokens + completion_tokens} tokens)",
            step="llm_generation",
            details={"tokens": {"prompt": prompt_tokens, "completion": completion_tokens}, "snippet": answer_snippet[:150]},
            trace_id=trace_id
        )


app_logger = StructuredLogger("agentic_rag")
