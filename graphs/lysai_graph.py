from langgraph.graph import StateGraph, END
from core.state import AgentState
from agents.planner import planner_node
from agents.executor import executor_node
from agents.reflector import reflector_node
from agents.summarizer import summarizer_node
from agents.tool_inspector import tool_inspector_node
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


# Build the graph to compile 
graph = StateGraph(AgentState)

graph.add_node("tool_inspector", tool_inspector_node)
graph.add_node("planner", planner_node)
graph.add_node("executor", executor_node)
graph.add_node("reflector", reflector_node)
graph.add_node("summarizer", summarizer_node)

graph.set_entry_point("tool_inspector")
graph.add_edge("tool_inspector", "planner")
graph.add_edge("planner", "executor")
graph.add_conditional_edges("executor", should_reflect, {
    "REFLECT": "reflector",
    END: "summarizer"
})
graph.add_edge("reflector", "executor")
graph.add_edge("summarizer", END)


app = graph.compile()


async def main():
    from core.state import AgentState

    print("Streaming agent reasoning")

    async for event in app.astream(AgentState(question="List the top actors in the database", plan=[])):
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