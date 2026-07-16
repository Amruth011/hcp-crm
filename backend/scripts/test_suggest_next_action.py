import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_core.messages import HumanMessage
from app.agent.graph import suggest_next_action, AgentState

def main():
    message_text = "Dr. Smith asked for a follow-up call next month"
    
    initial_form = {
        "hcp_id": 1,
        "sentiment": "positive",
        "outcomes": "Dr. Smith asked for a follow-up call next month"
    }
    
    print("--- Before ---")
    print(json.dumps(initial_form, indent=2))

    initial_state: AgentState = {
        "messages": [HumanMessage(content=message_text)],
        "interaction_form": initial_form,
        "confidence": 1.0,
        "active_hcp_candidates": [],
        "tool_trace": []
    }

    new_state = suggest_next_action(initial_state)

    print("\n--- After ---")
    print("Interaction Form:")
    print(json.dumps(new_state.get("interaction_form", {}), indent=2))
    
    print("\nTool Trace:")
    print(json.dumps(new_state.get("tool_trace", []), indent=2))

if __name__ == "__main__":
    main()
