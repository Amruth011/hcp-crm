import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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


def _build_messages(history, message):
    msgs = []
    for m in (history or []):
        role = m.get("role")
        content = m.get("content", "")
        if role == "user":
            msgs.append(HumanMessage(content=content))
        elif role == "assistant":
            msgs.append(AIMessage(content=content))
    if message:
        msgs.append(HumanMessage(content=message))
    return msgs


# ── Original blocking endpoint (kept for tests / backward compat) ─────────
@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    messages = _build_messages(request.history, request.message)
    initial_state = {
        "messages": messages,
        "interaction_form": request.interaction_form,
        "confidence": 1.0,
        "active_hcp_candidates": [],
        "tool_trace": [],
    }
    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    chat_response = ""
    if final_state.get("messages"):
        last = final_state["messages"][-1]
        if hasattr(last, "type") and last.type == "ai":
            chat_response = last.content

    return ChatResponse(
        interaction_form=final_state.get("interaction_form", {}),
        chat_response=chat_response,
        tool_trace=final_state.get("tool_trace", []),
    )


# ── Streaming SSE endpoint ────────────────────────────────────────────────
@router.post("/chat/message")
async def chat_message_stream(request: ChatRequest):
    """
    Runs the LangGraph agent and streams SSE events as each node completes.

    Event types:
      { type: "patch",      interaction_form: {...} }   – form changed
      { type: "tool_trace", tool_name, input_data, output_data }
      { type: "message",    content: "..." }             – final AI reply
      { type: "error",      detail: "..." }
      { type: "done" }
    """
    messages = _build_messages(request.history, request.message)
    initial_state = {
        "messages": messages,
        "interaction_form": request.interaction_form,
        "confidence": 1.0,
        "active_hcp_candidates": [],
        "tool_trace": [],
    }

    def event_stream():
        prev_form = request.interaction_form.copy()
        prev_trace_len = 0
        prev_msg_len = len(messages)

        try:
            for snapshot in graph.stream(initial_state, stream_mode="values"):
                # 1. Form patch — dispatch immediately so diff animation fires
                new_form = snapshot.get("interaction_form", {})
                if new_form != prev_form:
                    yield f"data: {json.dumps({'type': 'patch', 'interaction_form': new_form})}\n\n"
                    prev_form = new_form.copy()

                # 2. New tool-trace entries since last snapshot
                traces = snapshot.get("tool_trace", [])
                for trace in traces[prev_trace_len:]:
                    payload = {
                        "type": "tool_trace",
                        "tool_name": trace.get("tool_name", ""),
                        "input_data": trace.get("input_data", {}),
                        "output_data": trace.get("output", trace.get("output_data", {})),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                prev_trace_len = len(traces)

                # 3. New AI messages
                msgs = snapshot.get("messages", [])
                for msg in msgs[prev_msg_len:]:
                    if hasattr(msg, "type") and msg.type == "ai":
                        yield f"data: {json.dumps({'type': 'message', 'content': msg.content})}\n\n"
                prev_msg_len = len(msgs)

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
