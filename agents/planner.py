from core.state import AgentState
from core.utils import llm_json
from core.llm_client import BaseLLM, get_llm
from core.memory import search_similar, recent_successes

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

{memory_context}
"""

def planner_node(state: AgentState) -> AgentState:
    """
    Planner node that generates a plan and SQL candidate based on the question.
    """

    # Get memory context from similar past episodes
    memory_context = ""
    try:
        similar_episodes = search_similar(state.question, limit=3)
        recent_episodes = recent_successes(limit=2)
        
        if similar_episodes or recent_episodes:
            memory_context = "\nPrevious successful examples:"
            
            for episode in similar_episodes:
                if episode.get('sql') and episode.get('outcome') == 'success':
                    memory_context += f"\nQ: {episode['question']}\nSQL: {episode['sql']}\n"
                    
            for episode in recent_episodes:
                if episode.get('sql') and episode not in similar_episodes:
                    memory_context += f"\nRecent Q: {episode['question']}\nSQL: {episode['sql']}\n"
    except Exception as e:
        # If memory retrieval fails, continue without it
        memory_context = ""

    llm = get_llm()
    response = llm.generate(
        prompt=state.question,
        system_instruction=PLANNER_SYS.format(memory_context=memory_context),
        json_mode=True,
        temperature=0.3,
        max_retries=3,
    )
    # Parse the JSON response
    try:
        import json
        
        # First try to parse the text response directly (works for most LLMs including Ollama)
        try:
            parsed = json.loads(response.text.strip())
            print(f"Successfully parsed JSON from text response")
        except json.JSONDecodeError:
            # If text parsing fails, try the raw response structure
            if hasattr(response, 'raw') and isinstance(response.raw, dict):
                if 'response' in response.raw:
                    # Rev21 format: {"response": {"plan": [...], "sql_candidate": "...", ...}}
                    parsed = response.raw['response']
                    print(f"Using Rev21 format from raw response")
                elif 'message' in response.raw and 'content' in response.raw['message']:
                    # Ollama format: {"message": {"content": "..."}}
                    content = response.raw['message']['content']
                    parsed = json.loads(content.strip())
                    print(f"Successfully parsed JSON from Ollama message content")
                else:
                    parsed = response.raw
                    print(f"Using raw response directly")
            else:
                raise ValueError("No parseable JSON found")
        
        # Ensure parsed is a dictionary, not a list
        if isinstance(parsed, list):
            # If it's a list, take the first item or create empty dict
            parsed = parsed[0] if parsed else {}
        elif not isinstance(parsed, dict):
            # If it's not a dict or list, create empty dict
            parsed = {}
            
    except (json.JSONDecodeError, KeyError, AttributeError, ValueError) as e:
        print(f"Warning: Could not parse planner response: {e}")
        print(f"Raw response text: {response.text[:200]}...")
        print(f"Raw response structure: {type(response.raw)}")
        if hasattr(response, 'raw'):
            print(f"Raw response keys: {list(response.raw.keys()) if isinstance(response.raw, dict) else 'Not a dict'}")
        # Fallback to empty dict if parsing fails
        parsed = {}
    
    state.plan = parsed.get("plan", [])
    state.sql = parsed.get("sql_candidate", "")
    
    print(f"Planner extracted - Plan: {state.plan}, SQL: {state.sql}")
    
    state.history.append({
        "role": "planner",
        "content": response.text,
        "raw": response.raw,
    })
    return state