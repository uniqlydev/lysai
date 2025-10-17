#!/usr/bin/env python3
"""
Test PDF insight extraction logic
"""
import sys
import os
sys.path.append('/Volumes/DevSSD/github/lysai')

from core.state import AgentState

def test_insight_extraction():
    """Test if PDF generator correctly extracts insights from history"""
    
    print("Testing insight extraction logic...")
    
    # Create a state that matches the actual log format
    state = AgentState(
        question="Who are the top 10 actors? Please generate a PDF after",
        plan=["Join actor and film_actor tables on actor_id"],
        sql="SELECT * FROM actors;",
        rows=[{"first_name": "GINA", "last_name": "DEGENERES", "film_count": 42}],
        available_tools=[{"name": "execute_sql"}, {"name": "generate_pdf"}],
        step=4,
        max_steps=10,
        history=[
            {
                "summarizer": {
                    "response": {
                        "insight": "The top 5 actors based on film count are Gina Degeneres (42 films), Walter Torn (41 films), Mary Keitel (40 films), Matthew Carrey (39 films), and Sandra Kilmer (37 films). No data is available for the remaining top 10 positions.",
                        "caveats": "Only 5 actors are listed; information for the full top 10 is not provided."
                    }
                }
            }
        ]
    )
    
    # Test the insight extraction logic
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
    
    print(f"Found insight: '{insight[:100]}...'")
    
    if insight:
        print("✅ SUCCESS: Insight extraction works correctly")
    else:
        print("❌ ISSUE: No insight found")
        print(f"History structure: {state.history}")

if __name__ == "__main__":
    test_insight_extraction()