import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_core.messages import HumanMessage
from app.agent.graph import check_compliance, AgentState

def main():
    message_text = "told the HCP this drug cures all forms of the disease with no side effects"
    
    initial_form = {
        "topics_discussed": "told the HCP this drug cures all forms of the disease with no side effects",
        "outcomes": "HCP agreed to prescribe to all patients"
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

    new_state = check_compliance(initial_state)

    print("\n--- After ---")
    print("Interaction Form:")
    print(json.dumps(new_state.get("interaction_form", {}), indent=2))
    
    print("\nTool Trace:")
    print(json.dumps(new_state.get("tool_trace", []), indent=2))

if __name__ == "__main__":
    main()
