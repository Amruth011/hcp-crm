import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_core.messages import HumanMessage
from app.agent.graph import log_interaction, AgentState

def main():
    message_text = "Today I met with Dr. Smith and discussed product X efficacy. Sentiment was positive, I shared brochures."
    print(f"Input Message: '{message_text}'\n")

    initial_state: AgentState = {
        "messages": [HumanMessage(content=message_text)],
        "interaction_form": {},
        "confidence": 1.0,
        "active_hcp_candidates": [],
        "tool_trace": []
    }

    new_state = log_interaction(initial_state)

    print("--- Tool Result ---")
    
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
