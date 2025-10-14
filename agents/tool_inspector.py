# core/nodes/tool_inspector.py
from typing import Any, Dict, List
from core.state import AgentState
from core.mcp_client import get_tools  # <- returns Tool models from fastmcp

def _tool_to_dict(tool) -> Dict[str, Any]:
    # fastmcp Tool is a Pydantic model; fall back to attrs if not
    if hasattr(tool, "model_dump"):
        d = tool.model_dump()
        # normalize common fields for downstream code
        return {
            "name": d.get("name"),
            "description": d.get("description"),
            "parameters": d.get("inputSchema") or d.get("parameters") or d.get("schema"),
            "raw": d,
        }
    # very defensive fallback
    return {
        "name": getattr(tool, "name", None),
        "description": getattr(tool, "description", None),
        "parameters": getattr(tool, "inputSchema", None),
        "raw": tool.__dict__ if hasattr(tool, "__dict__") else str(tool),
    }

async def tool_inspector_node(state: AgentState) -> AgentState:
    """
    Asks the MCP server for tools, normalizes them to dicts,
    stores on state, and appends a human-readable summary to history.
    """
    try:
        tools = await get_tools()                # <-- await (no asyncio.run)
        tools_dicts: List[Dict[str, Any]] = [_tool_to_dict(t) for t in tools]

        # Make these the canonical representation other nodes consume
        state.available_tools = tools_dicts

        # Human-readable summary
        summary_lines = [
            f"- {t.get('name') or 'unknown'}: {t.get('description') or 'No description'}"
            for t in tools_dicts
        ]
        tools_text = "\n".join(summary_lines) if summary_lines else "No tools available"

        # Only put JSON-serializable content into history.raw
        state.history.append({
            "role": "tool_inspector",
            "content": f"Available tools:\n{tools_text}",
            "raw": {"tools_count": len(tools_dicts), "tools": [t["raw"] for t in tools_dicts]},
        })
        state.error = None
    except Exception as e:
        state.available_tools = []
        state.error = f"Tool inspection error: {e}"
        state.history.append({
            "role": "tool_inspector",
            "content": f"Failed to get available tools: {e}",
            "raw": {"error": str(e)},
        })
    return state