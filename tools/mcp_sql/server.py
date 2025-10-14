from fastmcp import FastMCP

from core.db_client import get_client

mcp = FastMCP("MCP SQL Server")


def _is_read_only(query: str) -> bool:
    """
    Query should be read-only SELECT and other safe statements are allowed
    """

    safe_statements = ["SELECT", "WITH", "EXPLAIN", "SHOW", "DESCRIBE"]
    query_upper = query.strip().upper()
    return any(query_upper.startswith(stmt) for stmt in safe_statements)


@mcp.tool("execute_sql")
def execute_sql(query: str) -> list[dict]:
    """
    Execute a read-only SQL query against the configured database.

    **Usage**
    - Input: a single SQL string beginning with SELECT, WITH, EXPLAIN, SHOW, or DESCRIBE.
    - Returns: a list of dictionaries representing the result rows.

    **Example**
        Input:
            "SELECT first_name, last_name
             FROM actor
             ORDER BY last_name
             LIMIT 10;"

        Output:
            [
                {"first_name": "Penelope", "last_name": "Guiness"},
                {"first_name": "Nick", "last_name": "Wahlberg"},
                ...
            ]

    Notes:
    - Mutating statements (INSERT, UPDATE, DELETE, DROP, etc.) are blocked.
    - The database connection is created via `core.db_client.get_client()`.
    """
    if not _is_read_only(query):
        return [{"error": "Only read-only queries are allowed"}]

    conn, cursor = get_client()
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # For stdio mode (default MCP transport):
    # mcp.run()
    
    # For HTTP mode with specific host and port:
    mcp.run(transport="http", host="localhost", port=8000)

    print("Available tools:")
    for tool in mcp.get_tools():
        print(f" - {tool['name']}: {tool['description']}")

    print("MCP SQL Server running on http://localhost:8000")