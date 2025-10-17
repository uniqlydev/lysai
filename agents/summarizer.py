from core.state import AgentState
from core.utils import llm_json
from core.memory import update_episode

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
    from core.llm_client import get_llm

    rows_preview = (state.rows or [])[:5]  

    user_prompt = f"Question: {state.question}\nRows: {rows_preview}"

    llm = get_llm()
    response = llm.generate(
        prompt=user_prompt,
        system_instruction=SUMMARIZER_SYS,
        json_mode=True,
        temperature=0.3,
        max_retries=3,
    )
    
    # Parse the JSON response
    try:
        import json
        j = json.loads(response.text.strip())
        
        # Ensure j is a dict, not a list or other type
        if not isinstance(j, dict):
            j = {"insight": str(j), "caveats": "Response was not a dictionary"}
            
    except json.JSONDecodeError:
        # Fallback to empty dict if parsing fails
        j = {"insight": "Failed to parse summary", "caveats": "JSON parsing error"}

    # Update episode with the generated insight
    if state.episode_id and isinstance(j, dict) and j.get("insight"):
        try:
            update_episode(state.episode_id, insight=j["insight"])
        except Exception as e:
            print(f"Warning: Could not update episode with insight: {e}")
            # Continue without failing the whole process

    state.history.append({
        "summarizer": j
    })

    return state 