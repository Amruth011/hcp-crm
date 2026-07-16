from typing import List, Dict, Any
from app.database import SessionLocal
from app.models.hcp import HCP

def find_hcps_by_name(name: str) -> List[Dict[str, Any]]:
    """Returns a list of matching HCPs as dictionaries."""
    with SessionLocal() as db:
        # Simple ilike search
        matches = db.query(HCP).filter(HCP.name.ilike(f"%{name}%")).all()
        
        return [
            {
                "id": m.id,
                "name": m.name,
                "specialty": m.specialty,
                "region": m.region
            }
            for m in matches
        ]

def get_past_interactions(hcp_id: int, limit: int = 3) -> List[Dict[str, Any]]:
    """Returns a list of recent interactions for an HCP."""
    from app.models.hcp import HCPInteraction
    with SessionLocal() as db:
        interactions = db.query(HCPInteraction)\
            .filter(HCPInteraction.hcp_id == hcp_id)\
            .order_by(HCPInteraction.created_at.desc())\
            .limit(limit)\
            .all()
            
        return [
            {
                "date": i.date,
                "type": i.interaction_type,
                "topics": i.topics_discussed,
                "outcomes": i.outcomes
            }
            for i in interactions
        ]

def log_tool_call(interaction_id: int | None, tool_name: str, input_data: dict, output_data: dict, before_state: dict, after_state: dict, confidence: float | None = 1.0, model_used: str = "llama-3.1-8b-instant") -> None:
    """Logs a tool call audit row to the agent_tool_calls table."""
    from app.models.hcp import AgentToolCall
    with SessionLocal() as db:
        audit = AgentToolCall(
            interaction_id=interaction_id,
            tool_name=tool_name,
            input=input_data,
            output=output_data,
            before_state=before_state,
            after_state=after_state,
            confidence=confidence,
            model_used=model_used
        )
        db.add(audit)
        db.commit()
