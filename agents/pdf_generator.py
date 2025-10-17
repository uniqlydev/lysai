from core.state import AgentState
from core.mcp_client import execute_tool
import json

PDF_SYS = """
You analyze data and insights to determine optimal PDF generation parameters.
Return ONLY valid JSON with keys:
- title: string (concise report title)
- chart_x_key: string (column name for x-axis, null if no chart needed)
- chart_y_key: string (column name for y-axis, null if no chart needed)
- chart_top_n: number (number of top items to show, default 10)
- chart_title: string (descriptive chart title)
Rules:
- Choose numeric columns for y-axis when creating charts
- Prefer categorical columns for x-axis
- Set chart keys to null if data is not suitable for visualization
- Output must be valid JSON, no markdown fences
"""

async def pdf_generator_node(state: AgentState) -> AgentState:
    """
    PDF Generator node that creates a PDF report from data and insights.
    """
    
    # Extract insight from history
    insight = ""
    for entry in state.history:
        if "summarizer" in entry:
            summary_data = entry["summarizer"]
            # Handle case where summarizer data is a list
            if isinstance(summary_data, list) and len(summary_data) > 0:
                first_item = summary_data[0]
                if isinstance(first_item, dict):
                    # Check for nested response structure
                    response_data = first_item.get("response", first_item)
                    insight = response_data.get("insight", "")
            elif isinstance(summary_data, dict):
                # Check for nested response structure
                response_data = summary_data.get("response", summary_data)
                insight = response_data.get("insight", "")
            break
    
    if not insight:
        state.error = "no_insight_available"
        return state
    
    # Determine PDF parameters using LLM
    from core.llm_client import get_llm
    
    # Prepare data context for LLM
    rows_sample = (state.rows or [])[:3]
    columns = list(rows_sample[0].keys()) if rows_sample else []
    
    user_prompt = f"""
Question: {state.question}
Insight: {insight}
Available columns: {columns}
Sample data: {rows_sample}
"""
    
    llm = get_llm()
    response = llm.generate(
        prompt=user_prompt,
        system_instruction=PDF_SYS,
        json_mode=True,
        temperature=0.3,
        max_retries=3,
    )
    
    # Parse LLM response
    try:
        pdf_params = json.loads(response.text.strip())
    except json.JSONDecodeError:
        pdf_params = {
            "title": "Data Analysis Report",
            "chart_x_key": None,
            "chart_y_key": None,
            "chart_top_n": 10,
            "chart_title": "Data Visualization"
        }
    
    # Prepare arguments for PDF generation tool
    tool_args = {
        "title": pdf_params.get("title", "Data Analysis Report"),
        "question": state.question,
        "insight": insight,
        "rows": state.rows or []
    }
    
    # Add chart parameters if specified
    if pdf_params.get("chart_x_key") and pdf_params.get("chart_y_key"):
        tool_args.update({
            "chart_x_key": pdf_params["chart_x_key"],
            "chart_y_key": pdf_params["chart_y_key"],
            "chart_top_n": pdf_params.get("chart_top_n", 10),
            "chart_title": pdf_params.get("chart_title")
        })
    
    # Execute PDF generation tool
    try:
        result = await execute_tool("generate_pdf", **tool_args)
        
        if result.get("success"):
            # Extract the actual result from MCP response
            content = result.get("content", [])
            if isinstance(content, list) and len(content) > 0:
                # Handle TextContent objects
                if hasattr(content[0], 'text'):
                    try:
                        pdf_result = json.loads(content[0].text)
                        state.history.append({
                            "role": "pdf_generator",
                            "content": f"PDF generated successfully at: {pdf_result.get('path', 'unknown')}",
                            "pdf_path": pdf_result.get("path"),
                            "raw": response.raw,
                        })
                        state.error = None
                    except json.JSONDecodeError:
                        state.error = "pdf_generation_parse_error"
                else:
                    # Direct dictionary response
                    pdf_result = content[0] if isinstance(content[0], dict) else {}
                    state.history.append({
                        "role": "pdf_generator", 
                        "content": f"PDF generated successfully at: {pdf_result.get('path', 'unknown')}",
                        "pdf_path": pdf_result.get("path"),
                        "raw": response.raw,
                    })
                    state.error = None
            else:
                state.error = "pdf_generation_empty_response"
        else:
            state.error = f"pdf_generation_failed: {result.get('error', 'unknown_error')}"
    
    except Exception as e:
        state.error = f"pdf_generation_exception: {str(e)}"
    
    return state