from core.state import AgentState
from core.utils import llm_json
from core.llm_client import BaseLLM, get_llm

PLANNER_SYS = """
You are a SQL planning agent for the Pagila Postgres schema.
Return ONLY valid JSON with keys:
- plan: array of short strings
- sql_candidate: string (a single SQL query)
- rationale: string
Rules:
- Use explicit table names and aliases.
- Prefer GROUP BY + ORDER BY + LIMIT for rankings.
- Output must be valid JSON, no markdown fences.
"""

def planner_node(state: AgentState) -> AgentState:
    """
    Planner node that generates a plan and SQL candidate based on the question.
    """

    llm = get_llm()
    response = llm.generate(
        prompt=state.question,
        system_instruction=PLANNER_SYS,
        json_mode=True,
        temperature=0.3,
        max_retries=3,
    )
    parsed = llm_json(response.text, user=state.question)
    state.plan = parsed.get("plan", {})
    state.sql = parsed.get("sql_candidate", "")
    state.history.append({
        "role": "planner",
        "content": response.text,
        "raw": response.raw,
    })
    return state