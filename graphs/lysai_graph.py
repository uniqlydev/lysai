from langgraph.graph import StateGraph, END
from core.state import AgentState
from agents.planner import planner_node
from agents.executor import executor_node
from agents.reflector import reflector_node
from agents.summarizer import summarizer_node
from agents.tool_inspector import tool_inspector_node
from agents.pdf_generator import pdf_generator_node
import asyncio

def should_reflect(state: AgentState) -> str: 
    """
    Determine if reflection is needed based on the current state.
    """
    # Count how many times we've reflected
    reflection_count = sum(1 for entry in state.history if 'reflector' in entry)
    
    # Prevent infinite loops by limiting reflections
    if reflection_count >= 3:
        return END
    
    if state.error or not state.rows:
        return "REFLECT"
    
    return END

def should_generate_pdf(state: AgentState) -> str:
    """
    Determine if PDF generation is requested or just return data.
    Checks for PDF-related keywords in the question or if explicitly requested.
    """
    # Check if PDF generation is explicitly requested in the question
    question_lower = state.question.lower()
    pdf_keywords = ["pdf", "report", "generate report", "create pdf", "export", "document"]
    
    if any(keyword in question_lower for keyword in pdf_keywords):
        return "GENERATE_PDF"
    
    # TODO: For testing, uncomment the next line to always generate PDFs
    return "GENERATE_PDF"
    
    # Default to just returning data without PDF generation
    # return END


# Build the graph to compile 
graph = StateGraph(AgentState)

graph.add_node("tool_inspector", tool_inspector_node)
graph.add_node("planner", planner_node)
graph.add_node("executor", executor_node)
graph.add_node("reflector", reflector_node)
graph.add_node("summarizer", summarizer_node)
graph.add_node("pdf_generator", pdf_generator_node)

graph.set_entry_point("tool_inspector")
graph.add_edge("tool_inspector", "planner")
graph.add_edge("planner", "executor")
graph.add_conditional_edges("executor", should_reflect, {
    "REFLECT": "reflector",
    END: "summarizer"
})
graph.add_edge("reflector", "executor")
graph.add_conditional_edges("summarizer", should_generate_pdf, {
    "GENERATE_PDF": "pdf_generator",
    END: END
})
graph.add_edge("pdf_generator", END)


app = graph.compile()


async def main():
    from core.state import AgentState

    print("Streaming agent reasoning")

    # Test with a question that should trigger PDF generation
    async for event in app.astream(AgentState(question="Generate a report on the top actors in the database", plan=[])):
        for node_name, state in event.items():
            print(f"node executed {node_name}:")
            print(f"  Question: {state.get('question', '')}")
            print(f"  Plan: {state.get('plan', {})}")
            print(f"  SQL: {state.get('sql', '')}")
            print(f"  Error: {state.get('error', None)}")
            print(f"  Rows: {state.get('rows', None)}")
            if state.get('available_tools'):
                print(f"  Available tools: {len(state.get('available_tools', []))} tools")
            print(f"  History entries: {len(state.get('history', []))}")
            if state.get('history'):
                print(f"  Latest history: {state['history'][-1]}")

            print ("-" * 40)

    print("done event\n")

if __name__ == "__main__":
    asyncio.run(main())