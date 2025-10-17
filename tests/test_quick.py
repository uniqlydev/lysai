#!/usr/bin/env python3
"""
Quick test for the PDF generation workflow
"""
import sys
import os
sys.path.append('/Volumes/DevSSD/github/lysai')

from core.state import AgentState
from agents.orchestrator import _fallback_decision

def test_pdf_decision():
    """Test if orchestrator correctly chooses GENERATE_PDF when conditions are met"""
    
    print("Testing fallback decision logic...")
    
    # Create a state that should trigger GENERATE_PDF
    state = AgentState(
        question="List all the top actors and generate a pdf report.",
        plan=["Get actor data", "Count films", "Generate report"],
        sql="SELECT * FROM actors;",
        rows=[{"name": "Actor 1", "films": 42}, {"name": "Actor 2", "films": 41}],
        available_tools=[{"name": "execute_sql"}, {"name": "generate_pdf"}],
        step=5,
        max_steps=10,
        history=[
            {
                "summarizer": {
                    "response": {
                        "insight": "Top actors are Actor 1 with 42 films and Actor 2 with 41 films.",
                        "caveats": "Based on film count only."
                    }
                }
            }
        ]
    )
    
    print(f"Question: {state.question}")
    print(f"Has data: {bool(state.rows)} ({len(state.rows)} rows)")
    print(f"Has insights: {len([h for h in state.history if 'summarizer' in h])} entries")
    print(f"PDF requested: {'pdf' in state.question.lower()}")
    
    # Test fallback logic
    decision = _fallback_decision(state)
    print(f"Fallback decision: {decision}")
    
    if decision == "GENERATE_PDF":
        print("✅ SUCCESS: Fallback correctly chose GENERATE_PDF")
    else:
        print(f"❌ ISSUE: Expected GENERATE_PDF, got {decision}")
        
    # Test without insights
    state_no_insights = AgentState(
        question="List all the top actors and generate a pdf report.",
        plan=["Get actor data", "Count films", "Generate report"],
        sql="SELECT * FROM actors;",
        rows=[{"name": "Actor 1", "films": 42}],
        available_tools=[{"name": "execute_sql"}, {"name": "generate_pdf"}],
        step=3,
        max_steps=10,
        history=[]
    )
    
    # Test case that should trigger EXECUTE (plan + SQL but no data)
    state_should_execute = AgentState(
        question="Who are the top 10 actors? Please generate a PDF after",
        plan=["Join actor and film_actor tables on actor_id", "Count films per actor"],
        sql="SELECT a.first_name, a.last_name, COUNT(fa.film_id) AS film_count FROM actor AS a JOIN film_actor AS fa ON a.actor_id = fa.actor_id GROUP BY a.actor_id ORDER BY film_count DESC LIMIT 10;",
        rows=None,  # No data yet
        available_tools=[{"name": "execute_sql"}, {"name": "generate_pdf"}],
        step=3,
        max_steps=10,
        error="no_sql_to_execute",  # This should be ignored
        history=[]
    )
    
    decision3 = _fallback_decision(state_should_execute)
    print(f"With plan+SQL but no data (error='no_sql_to_execute'), decision: {decision3}")
    
    if decision3 == "EXECUTE":
        print("✅ SUCCESS: Correctly chose EXECUTE when plan+SQL ready")
    else:
        print(f"❌ ISSUE: Expected EXECUTE, got {decision3}")

if __name__ == "__main__":
    test_pdf_decision()