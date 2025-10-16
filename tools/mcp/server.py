from fastmcp import FastMCP

from tools.mcp.tools.sql_tools import execute_sql
from tools.mcp.tools.pdf_tools import generate_pdf

mcp = FastMCP("Unified MCP Server")


# Register SQL tools
@mcp.tool("execute_sql")
def _execute_sql(query: str) -> list[dict]:
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
    return execute_sql(query)


# Register PDF visualization tools
@mcp.tool("generate_pdf")
def _generate_pdf(
    title: str,
    question: str,
    insight: str,
    rows: list[dict],
    chart_x_key: str | None = None,
    chart_y_key: str | None = None,
    chart_top_n: int = 10,
    chart_title: str | None = None
) -> dict:
    """
    Generate a PDF report from the provided data and insights.

    **Parameters**
    - title: The title of the report
    - question: The question that was answered
    - insight: Key findings and insights from the data
    - rows: List of dictionaries representing the data rows
    - chart_x_key: (Optional) Column name for chart X-axis
    - chart_y_key: (Optional) Column name for chart Y-axis
    - chart_top_n: (Optional) Number of top items to show in chart (default: 10)
    - chart_title: (Optional) Custom title for the chart

    **Returns**
    - A dictionary with "ok": True and "path": <file_path> on success
    """
    return generate_pdf(
        title=title,
        question=question,
        insight=insight,
        rows=rows,
        chart_x_key=chart_x_key,
        chart_y_key=chart_y_key,
        chart_top_n=chart_top_n,
        chart_title=chart_title
    )


if __name__ == "__main__":
    # For stdio mode (default MCP transport):
    # mcp.run()
    
    # For HTTP mode with specific host and port:
    mcp.run(transport="http", host="localhost", port=8000)

    print("Available tools:")
    for tool in mcp.get_tools():
        print(f" - {tool['name']}: {tool['description']}")

    print("Unified MCP Server running on http://localhost:8000")