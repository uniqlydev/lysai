from typing import Dict, Any
from core.state import AgentState
from core.mcp_client import sync_execute_sql
from core.memory import log_episode, update_episode


def executor_node(state: AgentState) -> AgentState:
    """
    Executor node that runs the SQL query using MCP client
    """

    # Ensure an episode exists 
    if state.episode_id is None: 
        state.episode_id = log_episode(
            question=state.question,
            plan=state.plan,
            sql=state.sql
        )

    if not state.sql:
        state.error = "no_sql_to_execute"
        return state
    
    try:
        # Execute SQL using MCP client
        result = sync_execute_sql(state.sql)
        
        if result.get("success"):
            # MCP returned successful result
            content = result.get("content", [])
            
            # Handle different content formats
            if isinstance(content, list) and len(content) > 0:
                # Check if it's a list of TextContent objects
                if hasattr(content[0], 'text'):
                    # Extract JSON from the text field
                    try:
                        import json
                        json_text = content[0].text
                        parsed_data = json.loads(json_text)
                        if isinstance(parsed_data, list):
                            state.rows = parsed_data
                            state.error = None
                        else:
                            state.rows = []
                            state.error = f"Expected list, got {type(parsed_data)}"
                    except json.JSONDecodeError as e:
                        state.rows = []
                        state.error = f"JSON parsing error: {str(e)}"
                # Check if it's already a list of dictionaries
                elif all(isinstance(item, dict) for item in content):
                    state.rows = content
                    state.error = None
                else:
                    state.rows = []
                    state.error = f"Unexpected content format: {type(content[0]) if content else 'empty'}"
            else:
                state.rows = []
                state.error = "Empty or invalid content"
        else:
            # MCP returned error
            state.rows = []
            state.error = result.get("error", "Unknown MCP error")
            
    except Exception as e:
        # Handle any unexpected errors
        state.rows = []
        state.error = f"Executor error: {str(e)}"

    # Update episode with execution results
    if state.episode_id:
        update_fields = {
            "sql": state.sql,
            "rows": state.rows,
            "error": state.error,
            "outcome": "success" if not state.error and state.rows else "error"
        }
        update_episode(state.episode_id, **update_fields)

    # Add to history
    state.history.append({
        "role": "executor", 
        "content": state.sql, 
        "raw": result if 'result' in locals() else {"error": state.error}
    })

    return state