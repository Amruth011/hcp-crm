from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.graph import build_graph

router = APIRouter()
graph = build_graph()

class ChatRequest(BaseModel):
    message: str
    interaction_form: Dict[str, Any]
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    interaction_form: Dict[str, Any]
    chat_response: str
    tool_trace: List[Dict[str, Any]]

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    messages = []
    if request.history:
        for msg in request.history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
                
    if request.message:
        messages.append(HumanMessage(content=request.message))
        
    initial_state = {
        "messages": messages,
        "interaction_form": request.interaction_form,
        "confidence": 1.0,
        "active_hcp_candidates": [],
        "tool_trace": []
    }
    
    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    chat_response = ""
    if final_state.get("messages"):
        last_msg = final_state["messages"][-1]
        if hasattr(last_msg, "content") and last_msg.type == "ai":
            chat_response = last_msg.content
            
    return ChatResponse(
        interaction_form=final_state.get("interaction_form", {}),
        chat_response=chat_response,
        tool_trace=final_state.get("tool_trace", [])
    )
