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
