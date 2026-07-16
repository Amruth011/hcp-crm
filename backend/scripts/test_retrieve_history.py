import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_core.messages import HumanMessage
from app.agent.graph import retrieve_interaction_history, log_interaction, AgentState

def test_direct_retrieval():
    print("\n--- TEST 1: Direct Retrieval (Dr. Alice Jones - assume unique) ---")
    message_text = "What did we last discuss with Dr. Alice Jones?"
    
    initial_state: AgentState = {
        "messages": [HumanMessage(content=message_text)],
        "interaction_form": {},
        "confidence": 1.0,
        "active_hcp_candidates": [],
        "tool_trace": []
    }

    new_state = retrieve_interaction_history(initial_state)

    print("Messages added:")
    for msg in new_state["messages"][1:]:
        print(f"- {msg.content}")
        
    print(f"Interaction Form changed? {len(new_state['interaction_form']) > 0}")

def test_ambiguity_via_log():
    print("\n--- TEST 2: Ambiguity via Log (Log Interaction -> Retrieve History) ---")
    message_text = "Today I met with Dr. Smith."
    
    initial_state: AgentState = {
        "messages": [HumanMessage(content=message_text)],
        "interaction_form": {},
        "confidence": 1.0,
        "active_hcp_candidates": [],
        "tool_trace": []
    }

    print("1. Running log_interaction...")
    state_after_log = log_interaction(initial_state)
    
    candidates = state_after_log.get("active_hcp_candidates", [])
    print(f"Candidates found: {len(candidates)}")
    if len(candidates) > 1:
        print("2. Routing to retrieve_interaction_history due to ambiguity...")
        final_state = retrieve_interaction_history(state_after_log)
        
        print("Messages added:")
        for msg in final_state["messages"][1:]:
            print(f"- {msg.content}")

def main():
    test_direct_retrieval()
    test_ambiguity_via_log()

if __name__ == "__main__":
    main()
