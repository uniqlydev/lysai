from core.state import AgentState
from core.utils import llm_json

REFLECTOR_SYS = """
You revise failing or weak SQL for Postgres (Pagila).
Return ONLY JSON:
- revised_sql: string
- reason: string
Rules:
- Fix syntax, joins, ambiguous columns.
- Add GROUP BY when ranking.
- Add LIMIT 5 for top-N queries.
"""

def reflector_node(state: AgentState) -> AgentState:
    """
    Reflector node that revises SQL queries based on execution errors or lack of results.
    """

    last_sql = state.sql or ""
    err = state.error or ("empty_result" if not state.rows else "unknown_error")

    if not err:
        return state # No error, no need to reflect
    
    user = f"lastSQL: {last_sql}\nerror: {err}"
    j = llm_json(REFLECTOR_SYS, user=user)

    if j.get("revised_sql"):
        state.sql = j["revised_sql"]
        state.history.append({
            "reflector": j
        })

    else:
        state.history.append({
            "reflector": {"note": "No revision made"}
        })
    return state 