from core.state import AgentState
from core.llm_client import get_llm
from core.semantic import get_learning_context
from typing import Dict, Any

def orchestrator_node(state: AgentState) -> AgentState:
    """
    Orchestrator node that reasons about what action to take next.
    This is the brain of the agentic system - it decides the workflow dynamically.
    Includes circuit breakers to prevent infinite loops.
    """
    # Circuit breaker: Check if we've exceeded max steps
    state.step += 1
    if state.step > state.max_steps:
        print("Max steps ({}) reached, completing task".format(state.max_steps))
        state.next_action = "DONE"
        state.history.append({
            "agent": "orchestrator",
            "action": "circuit_breaker",
            "reason": "max_steps_reached",
            "step": state.step
        })
        return state
    
    # Circuit breaker: Detect loops (same action repeated)
    recent_decisions = []
    for entry in state.history[-5:]:  # Check last 5 entries
        if isinstance(entry, dict) and entry.get('agent') == 'orchestrator':
            recent_decisions.append(entry.get('decision'))
    
    if len(recent_decisions) >= 3 and len(set(recent_decisions[-3:])) == 1:
        repeated_action = recent_decisions[-1]
        print(f"🔄 Loop detected: {repeated_action} repeated 3 times, forcing progression")
        state.next_action = _force_progression(state, repeated_action)
        state.history.append({
            "agent": "orchestrator", 
            "action": "loop_breaker",
            "repeated_action": repeated_action,
            "forced_action": state.next_action,
            "step": state.step
        })
        return state
    
    llm = get_llm()
    
    # Get learning context from semantic memory
    try:
        learning_context = get_learning_context(state.question)
    except Exception as e:
        print(f"Warning: Could not get learning context: {e}")
        learning_context = {'similar_patterns': [], 'relevant_insights': []}
    
    # Build context for decision making
    context = _build_decision_context(state, learning_context)
    
    # Get LLM to reason about next action
    prompt = f"""You are an intelligent orchestrator for a data analysis agent. Your job is to reason about what action to take next based on the current state.

CURRENT STATE:
{context}

AVAILABLE ACTIONS:
- INSPECT_TOOLS: Examine available database tools/tables (do this first if not done)
- PLAN: Create a step-by-step plan to answer the question
- EXECUTE: Execute SQL query to get data
- REFLECT: Analyze errors and improve the approach
- SUMMARIZE: Create a summary of results
- GENERATE_PDF: Create a PDF report
- DONE: Task is complete

REASONING GUIDELINES:
1. INSPECT_TOOLS: Only if available_tools is empty/None (not already done)
2. PLAN: If no clear plan exists and no similar patterns available
3. EXECUTE: If we have a plan AND SQL query AND no data yet (PRIORITIZE this!)
4. REFLECT: If there are REAL errors that need analysis (not state indicators like "no_sql_to_execute")
5. SUMMARIZE: If we have data but no insights yet (DON'T repeat if insights already exist)
6. GENERATE_PDF: If question mentions "PDF" AND we have data AND insights AND PDF not generated yet
7. DONE: If question is fully answered AND PDF is generated (if requested)

CRITICAL WORKFLOW: 
- If we have plan + SQL but no data: ALWAYS choose EXECUTE
- If PDF already generated: ALWAYS choose DONE (task complete)
- For PDF generation: MUST do SUMMARIZE first to generate insights, then GENERATE_PDF once
- Once insights exist, move to GENERATE_PDF immediately if PDF requested
- NEVER repeat GENERATE_PDF if PDF already generated successfully
- Ignore state indicators like "no_sql_to_execute" - these are not real errors
- Available tools: {"Present" if state.available_tools else "Missing"}
- SQL query: {"Present" if state.sql else "Missing"}  
- Data rows: {"Present" if state.rows else "Missing"}
- Error: {"Present" if state.error else "None"}

Based on the current state, what should the next action be?

Respond with just the action name (e.g., "PLAN", "EXECUTE", etc.) and a brief reason why."""

    try:
        response = llm.generate(prompt, temperature=0.1)
        decision_text = response.text.strip()
        
        # Parse the decision
        lines = decision_text.split('\n')
        action = lines[0].strip().upper()
        reason = '\n'.join(lines[1:]).strip() if len(lines) > 1 else "No reason provided"
        
        # Validate and set action
        valid_actions = {"INSPECT_TOOLS", "PLAN", "EXECUTE", "REFLECT", "SUMMARIZE", "GENERATE_PDF", "DONE"}
        
        # Clean up action text and try to extract valid action
        original_action = action
        if action not in valid_actions:
            # Try to find a valid action within the response text
            full_text = decision_text.upper()
            found_action = None
            
            for valid_action in valid_actions:
                if valid_action in full_text:
                    found_action = valid_action
                    break
            
            if found_action:
                action = found_action
                reason = f"Extracted '{action}' from: {original_action[:50]}..."
            else:
                action = _fallback_decision(state)
                reason = f"Invalid action '{original_action[:30]}...', using fallback: {action}"
        
        state.next_action = action
        
        # Add to history
        state.history.append({
            "agent": "orchestrator",
            "action": "decide_next_action", 
            "decision": action,
            "reasoning": reason,
            "step": state.step,
            "context_used": {
                "similar_patterns": len(learning_context.get('similar_patterns', [])),
                "relevant_insights": len(learning_context.get('relevant_insights', []))
            }
        })
        
        print(f"Orchestrator Decision: {action} (Step {state.step}/{state.max_steps})")
        print(f"Reasoning: {reason}")
        
        if learning_context.get('similar_patterns'):
            print(f"Found {len(learning_context['similar_patterns'])} similar patterns from memory")
        
        return state
        
    except Exception as e:
        print(f"Orchestrator error: {e}")
        # Fallback decision
        state.next_action = _fallback_decision(state)
        state.error = f"Orchestrator failed: {e}"
        state.history.append({
            "agent": "orchestrator",
            "action": "error_fallback",
            "error": str(e),
            "fallback_action": state.next_action,
            "step": state.step
        })
        return state

def _force_progression(state: AgentState, repeated_action: str) -> str:
    """Force progression when stuck in a loop"""
    if repeated_action == "INSPECT_TOOLS" and state.available_tools:
        return "PLAN"
    elif repeated_action == "PLAN" and state.plan:
        return "EXECUTE" 
    elif repeated_action == "EXECUTE" and state.sql:
        return "SUMMARIZE" if state.rows else "REFLECT"
    elif repeated_action == "REFLECT":
        return "DONE"  # Give up after too many reflections
    else:
        return "DONE"  # Default fallback

def _fallback_decision(state: AgentState) -> str:
    """Smart fallback when LLM fails or gives invalid action"""
    # Check if we have insights from summarizer
    has_insights = False
    for entry in state.history:
        if isinstance(entry, dict):
            if "summarizer" in entry:
                summary_data = entry["summarizer"]
                if isinstance(summary_data, dict):
                    response_data = summary_data.get("response", summary_data)
                    has_insights = bool(response_data.get("insight", "").strip())
                break
            elif entry.get("insight"):
                has_insights = True
                break
    
    # Check if PDF has been successfully generated
    pdf_generated = False
    for entry in state.history:
        if isinstance(entry, dict) and entry.get('role') == 'pdf_generator':
            if entry.get('pdf_path') or 'PDF generated successfully' in entry.get('content', ''):
                pdf_generated = True
                break
    
    # Check for real errors (not just state indicators)
    real_error = state.error and state.error not in ["no_sql_to_execute", "no_data", "no_plan"]
    
    # Priority logic
    if not state.available_tools:
        return "INSPECT_TOOLS"
    elif real_error and len([h for h in state.history if h.get('agent') == 'reflector']) < 2:
        return "REFLECT"
    elif not state.plan:
        return "PLAN"
    elif state.plan and state.sql and not state.rows:
        return "EXECUTE"  # We have SQL ready to execute
    elif "pdf" in state.question.lower() and state.rows and has_insights and pdf_generated:
        return "DONE"  # PDF has been generated successfully
    elif "pdf" in state.question.lower() and state.rows and has_insights:
        return "GENERATE_PDF"  # Prioritize PDF generation when we have data + insights
    elif state.rows and not has_insights:
        return "SUMMARIZE"
    else:
        return "DONE"

def _build_decision_context(state: AgentState, learning_context: Dict[str, Any]) -> str:
    """Build a comprehensive context string for decision making"""
    
    # Check if we have insights from summarizer
    has_insights = False
    for entry in state.history:
        if isinstance(entry, dict):
            # Check for summarizer responses in different formats
            if "summarizer" in entry:
                summary_data = entry["summarizer"]
                if isinstance(summary_data, dict):
                    response_data = summary_data.get("response", summary_data)
                    has_insights = bool(response_data.get("insight", "").strip())
                elif isinstance(summary_data, list) and len(summary_data) > 0:
                    first_item = summary_data[0]
                    if isinstance(first_item, dict):
                        has_insights = bool(first_item.get("insight", "").strip())
                break
            # Also check if any entry has insight directly
            elif entry.get("insight"):
                has_insights = True
                break
    
    # Check if PDF was requested in the question
    pdf_requested = "pdf" in state.question.lower()
    
    # Check if PDF has been successfully generated
    pdf_generated = False
    for entry in state.history:
        if isinstance(entry, dict) and entry.get('role') == 'pdf_generator':
            if entry.get('pdf_path') or 'PDF generated successfully' in entry.get('content', ''):
                pdf_generated = True
                break
    
    # Check for real errors vs state indicators
    real_error = state.error and state.error not in ["no_sql_to_execute", "no_data", "no_plan"]
    
    context_parts = [
        f"Question: {state.question}",
        f"PDF Requested: {'Yes' if pdf_requested else 'No'}",
        f"PDF Generated: {'Yes' if pdf_generated else 'No'}",
        f"Current Step: {state.step}/{state.max_steps}",
        f"Tools Available: {'Yes (' + str(len(state.available_tools)) + ' tools)' if state.available_tools else 'No'}",
        f"Plan Exists: {'Yes (' + str(len(state.plan)) + ' steps)' if state.plan else 'No'}",
        f"SQL Query: {'Yes' if state.sql else 'No'}",
        f"Has Results: {'Yes (' + str(len(state.rows)) + ' rows)' if state.rows else 'No'}",
        f"Has Insights: {'Yes' if has_insights else 'No'}",
        f"Has Error: {'Yes' if real_error else 'No'}",
    ]
    
    # Add execution history
    if state.history:
        recent_actions = []
        for entry in state.history[-5:]:
            if isinstance(entry, dict):
                agent = entry.get('agent', 'unknown')
                action = entry.get('action', entry.get('decision', 'unknown'))
                recent_actions.append(f"{agent}:{action}")
        context_parts.append(f"Recent Actions: {' -> '.join(recent_actions)}")
    
    # Add error information if present (only real errors)
    if real_error:
        context_parts.append(f"Current Error: {state.error[:100]}...")
    
    # Add similar patterns from memory
    if learning_context.get('similar_patterns'):
        context_parts.append("Similar Past Patterns:")
        for i, pattern in enumerate(learning_context['similar_patterns'][:2], 1):
            context_parts.append(f"  {i}. Q: {pattern['question'][:60]}...")
            if pattern.get('sql'):
                context_parts.append(f"     SQL: {pattern['sql'][:80]}...")
            context_parts.append(f"     Similarity: {pattern['similarity']:.2f}")
    
    # Add relevant insights
    if learning_context.get('relevant_insights'):
        context_parts.append("Relevant Insights from Memory:")
        for i, insight in enumerate(learning_context['relevant_insights'][:2], 1):
            context_parts.append(f"  {i}. {insight['insight'][:100]}...")
    
    return '\n'.join(context_parts)