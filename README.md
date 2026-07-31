# Sentinel

Sentinel is a lightweight incident monitoring and investigation system with:

- FastAPI backend for alert ingestion, incident tracking, and AI analysis
- SQLite persistence via SQLAlchemy
- Ollama-powered AI incident investigation and postmortem generation
- Next.js frontend dashboard for alert creation and incident review

## Local Setup

### Python backend

1. Activate the repository virtual environment:
   - Windows PowerShell:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - Windows Command Prompt:
     ```cmd
     .\.venv\Scripts\activate.bat
     ```

2. Install Python dependencies if needed:
   ```powershell
   pip install -r requirements.txt
   ```

3. Start the backend:
   ```powershell
   uvicorn backend.main:app --reload --port 8000
   ```

### Frontend

1. Change into the frontend directory:
   ```powershell
   cd frontend
   ```

2. Install dependencies if needed:
   ```powershell
   npm install
   ```

3. Start the frontend:
   ```powershell
   npm run dev
   ```

4. Open the app in the browser at:
   - `http://127.0.0.1:3000`

## Configuration

- Backend API: `http://127.0.0.1:8000`
- Frontend default assumes backend is available on port `8000`
- Ollama URL is configured through `OLLAMA_BASE_URL` (default: `http://127.0.0.1:11434`)
- Ollama model is configured through `OLLAMA_MODEL` (default: `llama3:latest`)

## Data Seeding

To populate the database with example commits:

```powershell
python seed.py
```

## How it works

- `POST /alert` ingests a new alert and stores an incident record
- The backend calls Ollama to generate structured analysis
- The frontend shows incident list, detail view, Slack-style preview, and resolve workflow

## Notes

- If Python is not on the PATH, use the local virtual environment Python at `.venv\Scripts\python.exe`
- The backend includes a parser for Ollama responses that handles JSON wrapped in markdown code fences
- The dashboard uses `NEXT_PUBLIC_BACKEND_URL` to override the backend URL if needed
