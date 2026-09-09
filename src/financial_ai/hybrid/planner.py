"""Execution planner orchestrating the dependency order between SQL and RAG branches."""
from typing import Dict, Any
from financial_ai.router.schemas import RouteType


class ExecutionPlanner:
    """Plans branch execution workflow based on route type."""

    def create_plan(self, route: RouteType, query: str) -> Dict[str, Any]:
        if route == RouteType.SQL_ONLY:
            return {"run_sql": True, "run_rag": False, "parallel": False}
        elif route == RouteType.RAG_ONLY:
            return {"run_sql": False, "run_rag": True, "parallel": False}
        else:  # HYBRID
            return {"run_sql": True, "run_rag": True, "parallel": True}
