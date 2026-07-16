import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_core.messages import HumanMessage
from app.agent.graph import edit_interaction, AgentState

def main():
    message_text = "Sorry, the name was actually Dr. John and the sentiment was negative."
    
    initial_form = {
        "hcp_name": "Dr. Smith",
        "sentiment": "positive",
        "topics_discussed": "Product X efficacy",
        "materials_shared": ["brochures"]
    }
    
    print("--- Before ---")
    print(json.dumps(initial_form, indent=2))
    
    print(f"\nInput Message: '{message_text}'\n")

    initial_state: AgentState = {
        "messages": [HumanMessage(content=message_text)],
        "interaction_form": initial_form,
        "confidence": 1.0,
        "active_hcp_candidates": [],
        "tool_trace": []
    }

    new_state = edit_interaction(initial_state)

    print("--- After ---")
    
    # Check if a new message was added (clarifying question)
    if len(new_state["messages"]) > 1:
        print("Ambiguity detected. Returned clarifying question:")
        print(f"Message: {new_state['messages'][-1].content}")
        print("\nActive HCP Candidates:")
        print(json.dumps(new_state.get("active_hcp_candidates", []), indent=2))
        
    print("\nInteraction Form:")
    print(json.dumps(new_state.get("interaction_form", {}), indent=2))
    
    print("\nTool Trace:")
    print(json.dumps(new_state.get("tool_trace", []), indent=2))

if __name__ == "__main__":
    main()
