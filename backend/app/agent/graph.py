from typing import TypedDict, List, Dict, Any
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq

from app.agent.schemas import LogInteractionExtraction, EditInteractionExtraction, ComplianceExtraction, NextActionExtraction
from app.agent.db import find_hcps_by_name, get_past_interactions

# 1. State Definition
class AgentState(TypedDict):
    messages: List[BaseMessage]
    interaction_form: Dict[str, Any]
    confidence: float
    active_hcp_candidates: List[Dict[str, Any]]
    tool_trace: List[Dict[str, Any]]

# 2. Tool Nodes (Stubs)
def log_interaction(state: AgentState) -> AgentState:
    print("Executing log_interaction tool...")
    llm = ChatGroq(model_name="llama-3.1-8b-instant")
    extractor = llm.with_structured_output(LogInteractionExtraction)
    
    last_message = state["messages"][-1].content if state["messages"] else ""
    if not last_message:
        return state
        
    extracted: LogInteractionExtraction = extractor.invoke(last_message)
    
    # Check DB for HCP
    hcp_id = None
    if extracted.hcp_name:
        matches = find_hcps_by_name(extracted.hcp_name)
        if len(matches) == 1:
            hcp_id = matches[0]["id"]
        elif len(matches) > 1:
            # Ambiguous match, do not patch form.
            clarification = f"I found multiple HCPs named {extracted.hcp_name} ("
            clarification += ", ".join([f"{m['specialty']}" for m in matches])
            clarification += "). Which one did you meet?"
            
            state["active_hcp_candidates"] = matches
            state["messages"].append(AIMessage(content=clarification))
            return state
            
    # Write patch
    form = state.get("interaction_form", {})
    if hcp_id:
        form["hcp_id"] = hcp_id
    if extracted.interaction_type:
        form["interaction_type"] = extracted.interaction_type
    if extracted.date:
        form["date"] = extracted.date
    if extracted.time:
        form["time"] = extracted.time
    if extracted.attendees:
        form["attendees"] = extracted.attendees
    if extracted.topics_discussed:
        form["topics_discussed"] = extracted.topics_discussed
    if extracted.sentiment:
        form["sentiment"] = extracted.sentiment
    if extracted.materials_shared:
        form["materials_shared"] = extracted.materials_shared
    if extracted.samples_distributed:
        form["samples_distributed"] = extracted.samples_distributed
        
    state["interaction_form"] = form
    
    # Add a tool trace
    state.setdefault("tool_trace", []).append({
        "tool_name": "log_interaction",
        "output": extracted.model_dump(),
        "after_state": form.copy()
    })
    
    return state

def edit_interaction(state: AgentState) -> AgentState:
    print("Executing edit_interaction tool...")
    llm = ChatGroq(model_name="llama-3.1-8b-instant")
    extractor = llm.with_structured_output(EditInteractionExtraction)
    
    last_message = state["messages"][-1].content if state["messages"] else ""
    if not last_message:
        return state
        
    # Provide the current state to the LLM so it knows what it's editing
    current_form = state.get("interaction_form", {})
    prompt = f"Current form state: {current_form}\n\nUser request: {last_message}\n\nExtract ONLY the fields the user explicitly wants to change."
    
    extracted: EditInteractionExtraction = extractor.invoke(prompt)
    
    # Check DB for HCP if it was changed
    hcp_id = None
    if extracted.hcp_name:
        matches = find_hcps_by_name(extracted.hcp_name)
        if len(matches) == 1:
            hcp_id = matches[0]["id"]
        elif len(matches) > 1:
            # Ambiguous match
            clarification = f"I found multiple HCPs named {extracted.hcp_name} ("
            clarification += ", ".join([f"{m['specialty']}" for m in matches])
            clarification += "). Which one did you mean?"
            
            state["active_hcp_candidates"] = matches
            state["messages"].append(AIMessage(content=clarification))
            return state
            
    # Write partial patch
    form = current_form.copy()
    
    if hcp_id is not None:
        form["hcp_id"] = hcp_id
        # Optionally update hcp_name in form if we store it
        form["hcp_name"] = extracted.hcp_name
    elif extracted.hcp_name is not None:
        form["hcp_name"] = extracted.hcp_name
        
    if extracted.interaction_type is not None:
        form["interaction_type"] = extracted.interaction_type
    if extracted.date is not None:
        form["date"] = extracted.date
    if extracted.time is not None:
        form["time"] = extracted.time
    if extracted.attendees is not None:
        form["attendees"] = extracted.attendees
    if extracted.topics_discussed is not None:
        form["topics_discussed"] = extracted.topics_discussed
    if extracted.sentiment is not None:
        form["sentiment"] = extracted.sentiment
    if extracted.materials_shared is not None:
        form["materials_shared"] = extracted.materials_shared
    if extracted.samples_distributed is not None:
        form["samples_distributed"] = extracted.samples_distributed
        
    state["interaction_form"] = form
    
    # Add a tool trace
    state.setdefault("tool_trace", []).append({
        "tool_name": "edit_interaction",
        "output": extracted.model_dump(),
        "after_state": form.copy()
    })
    
    return state

def check_compliance(state: AgentState) -> AgentState:
    print("Executing check_compliance tool...")
    
    # We only check compliance if there's an interaction form with relevant fields
    form = state.get("interaction_form", {})
    topics = form.get("topics_discussed", "")
    outcomes = form.get("outcomes", "")
    
    if not topics and not outcomes:
        return state
        
    llm = ChatGroq(model_name="llama-3.1-8b-instant")
    extractor = llm.with_structured_output(ComplianceExtraction)
    
    prompt = f"Analyze the following interaction details for off-label claims, exaggerated efficacy, or compliance risks.\nTopics: {topics}\nOutcomes: {outcomes}"
    extracted: ComplianceExtraction = extractor.invoke(prompt)
    
    # Write patch
    new_form = form.copy()
    new_form["compliance_flag"] = extracted.compliance_flag
    if extracted.rationale:
        new_form["compliance_rationale"] = extracted.rationale
        
    state["interaction_form"] = new_form
    
    # Add a tool trace
    state.setdefault("tool_trace", []).append({
        "tool_name": "check_compliance",
        "output": extracted.model_dump(),
        "after_state": new_form.copy()
    })
    
    return state

def suggest_next_action(state: AgentState) -> AgentState:
    print("Executing suggest_next_action tool...")
    
    form = state.get("interaction_form", {})
    sentiment = form.get("sentiment", "")
    outcomes = form.get("outcomes", "")
    hcp_id = form.get("hcp_id")
    
    if not outcomes:
        # Without outcomes, we don't have enough to suggest a good next action
        return state
        
    past_interactions = []
    if hcp_id is not None:
        past_interactions = get_past_interactions(hcp_id)
        
    llm = ChatGroq(model_name="llama-3.1-8b-instant")
    extractor = llm.with_structured_output(NextActionExtraction)
    
    prompt = f"Based on the following interaction details, suggest 1 to 3 short, plain-language follow-up actions for the sales rep.\n\n"
    prompt += f"Current Sentiment: {sentiment}\n"
    prompt += f"Current Outcomes: {outcomes}\n"
    
    if past_interactions:
        prompt += f"\nPast Interactions Context:\n{past_interactions}\n"
        
    extracted: NextActionExtraction = extractor.invoke(prompt)
    
    # Write patch
    new_form = form.copy()
    new_form["suggested_follow_ups"] = extracted.suggested_follow_ups
    
    state["interaction_form"] = new_form
    
    # Add a tool trace
    state.setdefault("tool_trace", []).append({
        "tool_name": "suggest_next_action",
        "output": extracted.model_dump(),
        "after_state": new_form.copy()
    })
    
    return state

def retrieve_interaction_history(state: AgentState) -> AgentState:
    print("Calling retrieve_interaction_history tool... (not implemented yet)")
    return state

# 3. Router Node
def router(state: AgentState) -> AgentState:
    escalate = False
    
    # Escalation Rule: confidence < 0.7
    if state.get("confidence", 1.0) < 0.7:
        escalate = True
    
    # Escalation Rule: message implies 3+ fields changing at once
    # (Placeholder logic for identifying complex multi-field edits)
    last_message = state["messages"][-1].content if state["messages"] else ""
    if "and" in last_message.lower() and len(last_message.split()) > 20: 
        # Very crude placeholder - will be refined
        escalate = True

    model_used = "llama-3.3-70b-versatile" if escalate else "llama-3.1-8b-instant"
    llm = ChatGroq(model_name=model_used)
    
    # We would bind our tools here: llm_with_tools = llm.bind_tools([...])
    # response = llm_with_tools.invoke(state["messages"])
    # 
    # For now, this is just a skeleton router.
    
    return state

# 4. Graph Construction
def build_graph():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("router", router)
    workflow.add_node("log_interaction", log_interaction)
    workflow.add_node("edit_interaction", edit_interaction)
    workflow.add_node("check_compliance", check_compliance)
    workflow.add_node("suggest_next_action", suggest_next_action)
    workflow.add_node("retrieve_interaction_history", retrieve_interaction_history)
    
    # Entry point
    workflow.set_entry_point("router")
    
    # Skeleton routing - everything goes to END for now until tools are wired up
    workflow.add_edge("router", END)
    workflow.add_edge("log_interaction", "check_compliance")
    workflow.add_edge("check_compliance", "suggest_next_action")
    workflow.add_edge("suggest_next_action", END)
    workflow.add_edge("edit_interaction", END)
    workflow.add_edge("retrieve_interaction_history", END)
    
    return workflow.compile()

# Helper for testing with scripts/eval_tools.py
def run_agent_turn(setup_form_state: dict, message: str) -> Any:
    """Entry point for the evaluation script."""
    # Placeholder return structure matching eval script expectations
    return {
        "interaction_form": setup_form_state,
        "tool_trace": [],
        "chat_response": "not implemented yet"
    }
