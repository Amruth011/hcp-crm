import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.database import engine
from app.models.hcp import HCP

def seed_db():
    print("Seeding database...")
    with Session(engine) as session:
        # Check if already seeded to avoid duplicates
        existing = session.query(HCP).count()
        if existing > 0:
            print(f"Database already contains {existing} HCPs. Skipping seed.")
            return

        hcps = [
            HCP(name="Dr. Smith", specialty="Cardiology", region="East Coast"),
            HCP(name="Dr. Smith", specialty="Neurology", region="West Coast"),
            HCP(name="Dr. Alice Jones", specialty="Pediatrics", region="Midwest"),
            HCP(name="Dr. Bob Miller", specialty="Oncology", region="South"),
        ]
        
        session.add_all(hcps)
        session.commit()
        print("Database seeded successfully with 4 HCPs.")

if __name__ == "__main__":
    seed_db()
