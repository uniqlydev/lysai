from typing import Dict, Any
from core.state import AgentState

def _mock_run(sql: str) -> Dict[str, Any]:
    """
    Mock function to simulate SQL execution.
    """

    return {
        "ok":True,
        "rows":[
            {"actor_id":1,"first_name":"PENELOPE","last_name":"GUINESS"},
            {"actor_id":2,"first_name":"NICK","last_name":"WAHLBERG"},
            {"actor_id":3,"first_name":"ED","last_name":"CHASE"},
        ],
        "error": None,
    }


def executor_node(state: AgentState) -> AgentState:
    """
    Executor node that runs the SQL query
    """

    if not state.sql:
        state.error = "no_sql_to_execute"
        return state
    
    res = _mock_run(state.sql)

    if res["ok"]:
        state.rows = res["rows"]
        state.error = None

    else:
        state.rows = None
        state.error = res["error"]

    state.history.append({"role": "executor", "content": state.sql, "raw": res})

    return state