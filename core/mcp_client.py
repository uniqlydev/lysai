import httpx
import json
from typing import Dict, Any, List
from fastmcp import Client

MCP_SERVER = "http://localhost:8000/mcp"

async def get_tools() -> list[dict]:
    """
    Get the list of available tools from MCP server
    """

    async with Client(MCP_SERVER) as client:
        tools = await client.list_tools()
        return tools

async def execute_tool(tool_name: str, **kwargs) -> dict:
    """
    Execute a tool by name with given arguments
    """
    try:
        async with Client(MCP_SERVER) as client:
            response = await client.call_tool(tool_name, kwargs)
            return {"success": True, "content": response.content}
                    
    except Exception as e:
        return {"success": False, "error": str(e)}

def sync_execute_sql(sql: str) -> dict:
    """
    Synchronous wrapper for SQL execution via MCP tools
    """
    import asyncio
    
    async def _async_execute_sql(sql: str) -> dict:
        try:
            # Assuming there's a SQL execution tool available via MCP
            # You may need to adjust the tool name based on your MCP server
            return await execute_tool("execute_sql", query=sql)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    return asyncio.run(_async_execute_sql(sql))
