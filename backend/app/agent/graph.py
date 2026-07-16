from typing import TypedDict, List, Dict, Any
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq

from app.agent.schemas import LogInteractionExtraction, EditInteractionExtraction, ComplianceExtraction, NextActionExtraction, HistoryQueryExtraction
from app.agent.db import find_hcps_by_name, get_past_interactions, log_tool_call

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
    model_name = "llama-3.1-8b-instant"
    llm = ChatGroq(model_name=model_name)
    extractor = llm.with_structured_output(LogInteractionExtraction)
    
    # Capture before_state
    before_state = state.get("interaction_form", {}).copy()
    
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
            # Ambiguous match, do not patch form. Pass candidates down.
            state["active_hcp_candidates"] = matches
            
            # Log the tool call before returning
            state.setdefault("tool_trace", []).append({
                "tool_name": "log_interaction",
                "output": extracted.model_dump(),
                "after_state": before_state
            })
            log_tool_call(
                interaction_id=before_state.get("id"),
                tool_name="log_interaction",
                input_data={"prompt": last_message},
                output_data=extracted.model_dump(),
                before_state=before_state,
                after_state=before_state,
                confidence=state.get("confidence", 1.0),
                model_used=model_name
            )
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
    
    
    # Add a tool trace and log to DB
    state.setdefault("tool_trace", []).append({
        "tool_name": "log_interaction",
        "output": extracted.model_dump(),
        "after_state": form.copy()
    })
    
    log_tool_call(
        interaction_id=form.get("id"), # Might be None if not saved yet
        tool_name="log_interaction",
        input_data={"prompt": last_message},
        output_data=extracted.model_dump(),
        before_state=before_state,
        after_state=form.copy(),
        confidence=state.get("confidence", 1.0),
        model_used=model_name
    )
    
    return state

def edit_interaction(state: AgentState) -> AgentState:
    print("Executing edit_interaction tool...")
    model_name = "llama-3.1-8b-instant"
    llm = ChatGroq(model_name=model_name)
    extractor = llm.with_structured_output(EditInteractionExtraction)
    
    # Capture before_state
    before_state = state.get("interaction_form", {}).copy()
    
    last_message = state["messages"][-1].content if state["messages"] else ""
    if not last_message:
        return state
        
    # Provide the current state to the LLM so it knows what it's editing
    prompt = f"Current form state: {before_state}\n\nUser request: {last_message}\n\nExtract ONLY the fields the user explicitly wants to change."
    
    extracted: EditInteractionExtraction = extractor.invoke(prompt)
    
    # Check DB for HCP if it was changed
    hcp_id = None
    if extracted.hcp_name:
        matches = find_hcps_by_name(extracted.hcp_name)
        if len(matches) == 1:
            hcp_id = matches[0]["id"]
        elif len(matches) > 1:
            # Ambiguous match, do not patch form. Pass candidates down.
            state["active_hcp_candidates"] = matches
            
            # Log the tool call before returning
            state.setdefault("tool_trace", []).append({
                "tool_name": "edit_interaction",
                "output": extracted.model_dump(),
                "after_state": before_state
            })
            log_tool_call(
                interaction_id=before_state.get("id"),
                tool_name="edit_interaction",
                input_data={"prompt": last_message},
                output_data=extracted.model_dump(),
                before_state=before_state,
                after_state=before_state,
                confidence=state.get("confidence", 1.0),
                model_used=model_name
            )
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
    
    
    # Add a tool trace and log to DB
    state.setdefault("tool_trace", []).append({
        "tool_name": "edit_interaction",
        "output": extracted.model_dump(),
        "after_state": form.copy()
    })
    
    log_tool_call(
        interaction_id=form.get("id"),
        tool_name="edit_interaction",
        input_data={"prompt": prompt},
        output_data=extracted.model_dump(),
        before_state=before_state,
        after_state=form.copy(),
        confidence=state.get("confidence", 1.0),
        model_used=model_name
    )
    
    return state

def check_compliance(state: AgentState) -> AgentState:
    print("Executing check_compliance tool...")
    model_name = "llama-3.1-8b-instant"
    
    # Capture before_state
    before_state = state.get("interaction_form", {}).copy()
    
    # We only check compliance if there's an interaction form with relevant fields
    form = state.get("interaction_form", {})
    topics = form.get("topics_discussed", "")
    outcomes = form.get("outcomes", "")
    
    if not topics and not outcomes:
        return state
        
    llm = ChatGroq(model_name=model_name)
    extractor = llm.with_structured_output(ComplianceExtraction)
    
    prompt = f"Analyze the following interaction details for off-label claims, exaggerated efficacy, or compliance risks.\nTopics: {topics}\nOutcomes: {outcomes}"
    extracted: ComplianceExtraction = extractor.invoke(prompt)
    
    # Write patch
    new_form = form.copy()
    new_form["compliance_flag"] = extracted.compliance_flag
    if extracted.rationale:
        new_form["compliance_rationale"] = extracted.rationale
        
    state["interaction_form"] = new_form
    
    
    # Add a tool trace and log to DB
    state.setdefault("tool_trace", []).append({
        "tool_name": "check_compliance",
        "output": extracted.model_dump(),
        "after_state": new_form.copy()
    })
    
    log_tool_call(
        interaction_id=new_form.get("id"),
        tool_name="check_compliance",
        input_data={"prompt": prompt},
        output_data=extracted.model_dump(),
        before_state=before_state,
        after_state=new_form.copy(),
        confidence=state.get("confidence", 1.0),
        model_used=model_name
    )
    
    return state

def suggest_next_action(state: AgentState) -> AgentState:
    print("Executing suggest_next_action tool...")
    model_name = "llama-3.1-8b-instant"
    
    # Capture before_state
    before_state = state.get("interaction_form", {}).copy()
    
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
        
    llm = ChatGroq(model_name=model_name)
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
    
    
    # Add a tool trace and log to DB
    state.setdefault("tool_trace", []).append({
        "tool_name": "suggest_next_action",
        "output": extracted.model_dump(),
        "after_state": new_form.copy()
    })
    
    log_tool_call(
        interaction_id=new_form.get("id"),
        tool_name="suggest_next_action",
        input_data={"prompt": prompt},
        output_data=extracted.model_dump(),
        before_state=before_state,
        after_state=new_form.copy(),
        confidence=state.get("confidence", 1.0),
        model_used=model_name
    )
    
    return state

def retrieve_interaction_history(state: AgentState) -> AgentState:
    print("Executing retrieve_interaction_history tool...")
    
    # Capture before_state
    before_state = state.get("interaction_form", {}).copy()
    
    candidates = state.get("active_hcp_candidates", [])
    if len(candidates) > 1:
        # Path A: Disambiguation fallback
        hcp_name = candidates[0].get("name", "the HCP")
        clarification = f"I found multiple HCPs named {hcp_name} ("
        clarification += ", ".join([f"{m['specialty']}" for m in candidates])
        clarification += "). Which one did you mean?"
        
        state["messages"].append(AIMessage(content=clarification))
        
        log_tool_call(
            interaction_id=before_state.get("id"),
            tool_name="retrieve_interaction_history",
            input_data={"candidates": [c.get("name") for c in candidates]},
            output_data={},
            before_state=before_state,
            after_state=before_state,
            confidence=state.get("confidence", 1.0),
            model_used="llama-3.1-8b-instant"
        )
        return state
        
    # Path B: History Query
    last_message = state["messages"][-1].content if state["messages"] else ""
    llm = ChatGroq(model_name="llama-3.1-8b-instant")
    extractor = llm.with_structured_output(HistoryQueryExtraction)
    
    prompt = f"User is asking about past interactions. Extract the HCP name they are asking about.\nUser query: {last_message}"
    extracted: HistoryQueryExtraction = extractor.invoke(prompt)
    
    if extracted.hcp_name:
        matches = find_hcps_by_name(extracted.hcp_name)
        if len(matches) == 1:
            hcp_id = matches[0]["id"]
            past = get_past_interactions(hcp_id, limit=5)
            if not past:
                state["messages"].append(AIMessage(content=f"I couldn't find any past interactions for {matches[0]['name']}."))
                return state
                
            summary_prompt = f"Summarize these past interactions for the user in a short, natural language response:\n{past}"
            summary_response = llm.invoke(summary_prompt)
            state["messages"].append(AIMessage(content=summary_response.content))
        elif len(matches) > 1:
            # Re-use Path A logic
            state["active_hcp_candidates"] = matches
            hcp_name = matches[0].get("name", "the HCP")
            clarification = f"I found multiple HCPs named {hcp_name} ("
            clarification += ", ".join([f"{m['specialty']}" for m in matches])
            clarification += "). Which one did you mean?"
            state["messages"].append(AIMessage(content=clarification))
        else:
            state["messages"].append(AIMessage(content=f"I couldn't find any HCP named {extracted.hcp_name}."))
            
    log_tool_call(
        interaction_id=state.get("interaction_form", {}).get("id"),
        tool_name="retrieve_interaction_history",
        input_data={"prompt": prompt} if 'prompt' in locals() else {"candidates": [c.get("name") for c in candidates]},
        output_data=extracted.model_dump() if 'extracted' in locals() else {},
        before_state=before_state,
        after_state=state.get("interaction_form", {}).copy(),
        confidence=state.get("confidence", 1.0),
        model_used=model_name if 'model_name' in locals() else "llama-3.1-8b-instant"
    )
            
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
def after_log_interaction(state: AgentState) -> str:
    if len(state.get("active_hcp_candidates", [])) > 1:
        return "retrieve_interaction_history"
    return "check_compliance"

def after_edit_interaction(state: AgentState) -> str:
    if len(state.get("active_hcp_candidates", [])) > 1:
        return "retrieve_interaction_history"
    return END

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
    workflow.add_conditional_edges("log_interaction", after_log_interaction)
    workflow.add_conditional_edges("edit_interaction", after_edit_interaction)
    workflow.add_edge("check_compliance", "suggest_next_action")
    workflow.add_edge("suggest_next_action", END)
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
