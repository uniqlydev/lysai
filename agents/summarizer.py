from core.state import AgentState
from core.utils import llm_json

SUMMARIZER_SYS = """
You convert tabular rows into a concise insight (<=120 words).
Return ONLY JSON:
- insight: string
- caveats: string (optional)
No code or markdown, just text.
"""

def summarizer_node(state: AgentState) -> AgentState:
    """
    Summarizer Node that generates insights from tabular data.
    """

    rows_preview = (state.rows or [])[:5]  

    user = f"Question: {state.question}\nRows: {rows_preview}"

    j = llm_json(SUMMARIZER_SYS, user=user)

    state.history.append({
        "summarizer": j
    })

    return state 