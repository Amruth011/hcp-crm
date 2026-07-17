# HCP CRM Interaction Assistant

An AI-powered Customer Relationship Management (CRM) assistant built for pharmaceutical sales representatives to seamlessly log and manage interactions with Healthcare Professionals (HCPs). By leveraging state-of-the-art Large Language Models (LLMs) and structured extraction, the system automatically translates conversational user chat or voice transcripts into structured CRM records, performs compliance checks for off-label claims, suggests next actions based on past discussions, and retrieves interaction history.

---

## 🚀 Live Deployment Links

* **Frontend Web Application (CDN Hosted - Instantly Loaded)**: [https://hcp-crm-frontend-pgi9.onrender.com](https://hcp-crm-frontend-pgi9.onrender.com)
* **Backend Web Service API**: [https://hcp-crm-backend-pts2.onrender.com](https://hcp-crm-backend-pts2.onrender.com)

---

## ⚙️ Architecture Diagram

```
+-------------------------------------------------------------+
|                       React / Redux UI                      |
|             (Port 5173 - App.jsx / Redux Store)             |
+------------------------------+------------------------------+
                               |
                               | (HTTP POST / SSE Streaming)
                               v
+-------------------------------------------------------------+
|                        FastAPI Backend                      |
|                  (Port 8000 - chat.py router)               |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                      LangGraph Workflow                     |
|                   (graph.py - State Graph)                  |
+----------+-------------------+-------------------+----------+
           |                   |                   |
           | (SQLAlchemy)      | (Structured API)  | (Structured API)
           v                   v                   v
+------------------+   +---------------+   +------------------+
|  Neon Postgres   |   |   Groq API    |   |     Groq API     |
|   Database URL   |   |  (Llama 3.3)  |   |    (Llama 3.1)   |
|   (DB Storage)   |   | (Extraction)  |   | (Chat Response)  |
+------------------+   +---------------+   +------------------+
```

---

## 🛠️ Key Technical Implementations & Fixes

### 1. HTTP/2 Connection Error Resolution
* **The Problem**: Groq Python SDK relies on `httpx` which defaults to HTTP/2 negotiation. In cloud environments like Render or behind proxy servers, HTTP/2 handshakes are frequently dropped, leading to `groq.APIConnectionError: Connection error.`.
* **The Fix**: Configured the LangGraph engine to instantiate `ChatGroq` with a custom `httpx.Client` that explicitly disables HTTP/2 (`http2=False`), ensuring robust connection pool reuse and stability:
  ```python
  _http_client = httpx.Client(transport=httpx.HTTPTransport(http2=False))
  ```

### 2. Environment Variable Sanitization
* **The Problem**: Accidental trailing whitespace or newline characters (`\n`) copied into dashboard settings cause `LocalProtocolError: Illegal header value` when building the authorization headers.
* **The Fix**: Implemented automatic string cleaning (`.strip()`) on startup for critical credentials (`GROQ_API_KEY`, `DATABASE_URL`) in both `main.py` and `database.py`.

### 3. CORS Policy Whitelisting
* **The Fix**: Configured the FastAPI CORS middleware origins to allow both the localhost addresses and the unique static CDN frontend domain: `https://hcp-crm-frontend-pgi9.onrender.com`.

---

## 🤖 The 5-Agent LangGraph Workflow

The assistant consists of 5 specialized agents structured as LangGraph nodes:

1. **`log_interaction` (Extraction Agent)**: Classifies and parses meeting transcripts to extract structured fields (HCP name, date, interaction type, attendees, topics discussed, sentiment, materials shared, samples distributed, outcomes, and follow-ups).
2. **`edit_interaction` (Patching Agent)**: Targets specific corrections provided by the rep and merges them with the existing form state without modifying untouched fields.
3. **`retrieve_interaction_history` (Context Continuity Agent)**: Queries Neon PostgreSQL for prior interaction records to summarize history. It triggers name disambiguation if a doctor's name is ambiguous (e.g., Cardiology vs. Neurology Dr. Smiths).
4. **`check_compliance` (Risk Management Agent)**: Runs automatically after logging to evaluate notes for off-label claims or exaggerated efficacy, raising review flags and writing compliance rationales.
5. **`suggest_next_action` (Recommendation Agent)**: Suggests follow-up steps based on sentiment, outcomes, and historical context.

---

## 💻 Local Setup Steps

### 1. Configure Environment Variables
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://<username>:<password>@<host>/<database>?sslmode=require
GROQ_API_KEY=gsk_your_key_here
```

### 2. Backend Setup
Navigate to the `backend` folder, install requirements, run migrations, and seed HCPs:
```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
source .venv/bin/activate    # macOS/Linux

pip install -r requirements.txt
alembic upgrade head
python scripts/seed_hcps.py
```

### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend
npm install
```

### 4. Run Locally
* **Backend**: `uvicorn app.main:app --reload --port 8000` (from `backend/` directory)
* **Frontend**: `npm run dev` (from `frontend/` directory)

---

## 🧪 Verification & Testing

### Isolated Script Testing
Run test scripts to test each node separately:
```bash
python scripts/test_log_interaction.py
python scripts/test_edit_interaction.py
python scripts/test_check_compliance.py
python scripts/test_suggest_next_action.py
python scripts/test_retrieve_history.py
```
