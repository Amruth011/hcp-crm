import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(dotenv_path="../.env")

app = FastAPI(title="HCP CRM API")

# Configure CORS
origins = ["http://localhost:5173", "http://127.0.0.1:5173", "https://hcp-crm-frontend.onrender.com"]
cors_allowed = os.getenv("CORS_ALLOWED_ORIGINS")
if cors_allowed:
    origins.extend([o.strip() for o in cors_allowed.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import chat

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "HCP CRM Backend is running"}

@app.get("/api/diagnose")
def diagnose_connections():
    import os
    from app.database import SessionLocal
    from sqlalchemy import text
    from langchain_groq import ChatGroq

    db_status = "unknown"
    groq_status = "unknown"

    # Test Database
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {type(e).__name__} - {str(e)}"

    # Test Groq
    try:
        # Check API key presence
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            groq_status = "error: GROQ_API_KEY env var is not set"
        else:
            llm = ChatGroq(model_name="llama-3.1-8b-instant")
            response = llm.invoke("say hello")
            groq_status = f"ok: {response.content}"
    except Exception as e:
        groq_status = f"error: {type(e).__name__} - {str(e)}"

    return {
        "database": db_status,
        "groq": groq_status,
        "groq_api_key_length": len(api_key) if api_key else 0,
        "database_url_length": len(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else 0
    }

app.include_router(chat.router, prefix="/api", tags=["chat"])

# Serve static files from frontend/dist
frontend_dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))

if os.path.exists(frontend_dist_path):
    # Mount assets folder for JS/CSS files
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_path, "assets")), name="assets")
    
    # Catch-all route to serve index.html for frontend client-side routing
    @app.get("/{catchall:path}")
    def serve_frontend(catchall: str):
        if catchall.startswith("api/") or catchall.startswith("docs") or catchall.startswith("openapi.json"):
            return {"error": "Not Found"}
        return FileResponse(os.path.join(frontend_dist_path, "index.html"))
