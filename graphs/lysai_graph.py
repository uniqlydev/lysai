from langgraph.graph import StateGraph, END
from core.state import AgentState
from agents.planner import planner_node
from agents.executor import executor_node
from agents.reflector import reflector_node
from agents.summarizer import summarizer_node
from agents.tool_inspector import tool_inspector_node
from agents.pdf_generator import pdf_generator_node
from agents.orchestrator import orchestrator_node
from core.memory import init_database as init_memory
import asyncio
import argparse
import os

def route_next_action(state: AgentState) -> str:
    """
    Route to the next action based on orchestrator's decision.
    The orchestrator reasons about what to do next.
    """
    # If orchestrator hasn't made a decision yet, something's wrong
    if not hasattr(state, 'next_action') or not state.next_action:
        return END
    
    next_action = state.next_action.upper()
    
    # Map orchestrator decisions to graph nodes
    action_map = {
        "INSPECT_TOOLS": "tool_inspector",
        "PLAN": "planner", 
        "EXECUTE": "executor",
        "REFLECT": "reflector",
        "SUMMARIZE": "summarizer",
        "GENERATE_PDF": "pdf_generator",
        "DONE": END,
        "END": END
    }
    
    return action_map.get(next_action, END)

# Build the graph
graph = StateGraph(AgentState)
init_memory()

# Add all nodes
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("tool_inspector", tool_inspector_node)
graph.add_node("planner", planner_node)
graph.add_node("executor", executor_node)
graph.add_node("reflector", reflector_node)
graph.add_node("summarizer", summarizer_node)
graph.add_node("pdf_generator", pdf_generator_node)

# Start with orchestrator
graph.set_entry_point("orchestrator")

# All nodes flow back to orchestrator for next decision (except END)
graph.add_conditional_edges("orchestrator", route_next_action, {
    "tool_inspector": "tool_inspector",
    "planner": "planner",
    "executor": "executor", 
    "reflector": "reflector",
    "summarizer": "summarizer",
    "pdf_generator": "pdf_generator",
    END: END
})

# All worker nodes return to orchestrator for next decision
graph.add_edge("tool_inspector", "orchestrator")
graph.add_edge("planner", "orchestrator")
graph.add_edge("executor", "orchestrator")
graph.add_edge("reflector", "orchestrator")
graph.add_edge("summarizer", "orchestrator")
graph.add_edge("pdf_generator", "orchestrator")

app = graph.compile()

async def main():
    parser = argparse.ArgumentParser(description='Run LysAI with different LLM backends')
    parser.add_argument('--llm', choices=['rev21', 'gemini'], default='rev21',
                       help='Choose LLM backend (default: rev21)')
    parser.add_argument('--question', type=str, 
                       default="List all the top actors and generate a pdf report.",
                       help='Question to ask the agent')
    parser.add_argument('--no-fallback', action='store_true',
                       help='Disable LLM fallback functionality')
    
    args = parser.parse_args()
    
    # Set environment variables based on arguments
    os.environ['LLM_BACKEND'] = args.llm
    if args.no_fallback:
        os.environ['LLM_FALLBACK_ENABLED'] = 'false'
    
    print(f"Using LLM Backend: {args.llm}")
    print(f"Fallback Enabled: {not args.no_fallback}")
    print("Streaming agentic reasoning")

    async for event in app.astream(AgentState(question=args.question, plan=[])):
        for node_name, state in event.items():
            print(f"Node executed: {node_name}")
            print(f"  Question: {state.get('question', '')}")
            if hasattr(state, 'next_action'):
                print(f"  Next Action: {state.next_action}")
            print(f"  Plan: {state.get('plan', [])}")
            print(f"  SQL: {state.get('sql', '')}")
            print(f"  Error: {state.get('error', None)}")
            if state.get('rows'):
                print(f"  Rows: {len(state.get('rows', []))} results")
            if state.get('available_tools'):
                print(f"  Available tools: {len(state.get('available_tools', []))} tools")
            print(f"  History entries: {len(state.get('history', []))}")
            if state.get('history'):
                print(f"  Latest history: {state['history'][-1]}")
            print("-" * 50)

    print("Agent completed task!")

if __name__ == "__main__":
    asyncio.run(main())