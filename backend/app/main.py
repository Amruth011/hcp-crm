import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(dotenv_path="../.env")

app = FastAPI(title="HCP CRM API")

# Configure CORS
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
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
