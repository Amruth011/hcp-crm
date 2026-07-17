import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(dotenv_path="../.env")

# Strip whitespace and trailing newlines from crucial environment variables
for env_var in ["GROQ_API_KEY", "DATABASE_URL"]:
    val = os.getenv(env_var)
    if val:
        os.environ[env_var] = val.strip()

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
