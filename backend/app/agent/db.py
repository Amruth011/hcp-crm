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
