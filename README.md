# HCP CRM Interaction Assistant

An AI-powered Customer Relationship Management (CRM) assistant built for pharmaceutical sales representatives to seamlessly log and manage interactions with Healthcare Professionals (HCPs). By leveraging state-of-the-art Large Language Models (LLMs) and structured extraction, the system automatically translates conversational user chat or voice transcripts into structured CRM records (handling multilingual inputs such as Kannada), performs compliance checks for off-label claims, suggests next actions based on past discussions, and retrieves interaction history with built-in doctor name disambiguation.

---

## Architecture Diagram

```
+-------------------------------------------------------------+
|                       React / Redux UI                      |
|                 (Port 5173 - App.jsx / Redux)               |
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

## Setup Steps

### 1. Prerequisites
Ensure you have the following installed on your system:
- **Node.js** (v18 or higher)
- **Python** (v3.10 or higher)
- A **Neon Postgres** database (or any PostgreSQL instance)
- A **Groq API Key** (for Llama models)

### 2. Configure Environment Variables
Create a file named `.env` in the project root directory and add your credentials:
```env
# PostgreSQL connection URI
DATABASE_URL=postgresql://<username>:<password>@<host>/<database>?sslmode=require

# Groq API Key
GROQ_API_KEY=gsk_your_key_here
```

### 3. Backend Setup
Navigate to the `backend` folder, set up a virtual environment, install dependencies, run migrations, and seed HCP data:
```bash
# Go to backend
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations (Alembic)
alembic upgrade head

# Seed initial HCP data
python scripts/seed_hcps.py
```

### 4. Frontend Setup
In a new terminal window, navigate to the `frontend` folder and install packages:
```bash
cd frontend
npm install
```

### 5. Running the Application
Start both the backend FastAPI server and the Vite dev server.

- **Start Backend** (from `backend` directory):
  ```bash
  .venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
  ```
- **Start Frontend** (from `frontend` directory):
  ```bash
  npm run dev
  ```

Open your browser and navigate to `http://localhost:5173/` to use the application.

---

## Programmatic Verification (Testing via cURL)

You can test each of the five functional agent nodes directly by sending HTTP POST requests to the `/api/chat` endpoint without opening a browser. 

### 1. Verify `log_interaction`
This tool parses user meeting descriptions and populates CRM form fields.
```bash
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{
           "message": "Today I met with Dr. Arun, discussed product X efficacy, sentiment was positive, and I shared brochures.",
           "interaction_form": {},
           "history": []
         }'
```
*Expected Output:* The JSON response will contain a `tool_trace` log indicating `log_interaction` has run, and the `interaction_form` will be populated with extracted values.

### 2. Verify `edit_interaction`
This tool handles user corrections by targeting and patching specific form fields.
```bash
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{
           "message": "Actually the date was yesterday and the sentiment was neutral.",
           "interaction_form": {
             "hcp_name": "Dr. John Smith",
             "interaction_type": "meeting",
             "date": "today",
             "sentiment": "positive"
           },
           "history": []
         }'
```
*Expected Output:* The `interaction_form` will be returned with `date` changed to "yesterday" and `sentiment` changed to "neutral", while keeping other fields intact.

### 3. Verify `retrieve_interaction_history` (with ambiguous HCP names)
This tool queries past records and triggers name disambiguation when multiple HCPs match.
```bash
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{
           "message": "What did we last discuss with Dr. Smith?",
           "interaction_form": {},
           "history": []
         }'
```
*Expected Output:* The assistant responds with a clarifying prompt asking which specialty/HCP you meant (e.g. Cardiology or Dermatology), and lists candidate profiles in `active_hcp_candidates`.

### 4. Verify `check_compliance`
This tool triggers automatically after new interaction details are logged to identify regulatory risks.
```bash
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{
           "message": "Met Dr. Arun. I told the doctor that Product X completely cures all heart disease with zero side effects.",
           "interaction_form": {},
           "history": []
         }'
```
*Expected Output:* The returned `interaction_form` will show `"compliance_flag": "review"` and a `"compliance_rationale"` explaining the off-label/exaggerated claim violation.

### 5. Verify `suggest_next_action`
This tool recommends follow-ups based on sentiment, outcomes, and past interactions.
```bash
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{
           "message": "Met Dr. Arun. Efficacy discussed and he agreed to prescribe it next month.",
           "interaction_form": {},
           "history": []
         }'
```
*Expected Output:* The form response will contain a list of recommended actions in `suggested_follow_ups` (e.g. following up in two weeks, sharing clinical trials).

---

## Design Rationale

While the core specification only required logging and editing features, the addition of three extra agents ensures that this system operates as a **production-grade enterprise solution**:

*   **`check_compliance` (Risk Guardrails)**: Pharmaceutical representatives operate in a highly regulated domain. Inadvertently claiming exaggerated efficacy or promoting off-label usage is a major legal risk. Real-time compliance checking serves as an immediate safety guardrail for the sales team.
*   **`suggest_next_action` (Proactive Sales Support)**: Sales representatives often log meetings rapidly between visits. Having the AI analyze outcomes to instantly recommend follow-up steps improves pipeline efficiency and rep productivity.
*   **`retrieve_interaction_history` (Context Continuity)**: Reps rarely meet an HCP in a vacuum. Disambiguating doctor names and providing a summary of prior discussions before logging new ones ensures accurate, contextual updates.
