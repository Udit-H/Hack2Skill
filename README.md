# ⚖️ Sahayak — Last Mile Justice Navigator

An AI-powered legal crisis navigator that helps individuals facing eviction navigate legal procedures, generate official documents, and find emergency shelter — all with a privacy-first, trauma-informed approach.

> **MVP Scope:** Currently focused on **illegal eviction in Delhi**, with two active agents (Legal + Shelter).

---

## 🏗️ Architecture

```
Hack2Skill/
├── backend/                  # FastAPI + Multi-Agent System
│   ├── agents/
│   │   └── legal_agent.py    # LLM-powered legal workflow agent
│   ├── core/
│   │   ├── orchestrator.py   # Agent routing & handoff engine
│   │   ├── memory.py         # Redis-backed conversation memory + L2 summarization
│   │   ├── ocr_service.py    # AWS Textract OCR integration
│   │   └── rag_service.py    # RAG pipeline (stub)
│   ├── models/               # Pydantic data models
│   │   ├── session.py        # Global session state
│   │   ├── legal.py          # Legal agent state & draft payloads
│   │   ├── triage.py         # Crisis triage state
│   │   ├── shelter.py        # Shelter profiles
│   │   └── enums.py          # Crisis categories, document types
│   ├── prompts/              # Jinja2 system prompts
│   ├── templates/            # Legal document HTML templates
│   ├── services/             # External service integrations
│   ├── config/config.py      # Pydantic settings (env-driven)
│   ├── main.py               # FastAPI server & API endpoints
│   └── test_cli.py           # Interactive CLI test harness
├── frontend/                 # Vite + React SPA
│   └── src/
│       ├── components/       # Chat UI, Panic Button, Sidebar, etc.
│       ├── hooks/useChat.js  # Chat state management
│       ├── utils/api.js      # REST API client
│       └── index.css         # Trauma-informed design system
└── documentation/
    ├── requirements.md       # Formal requirements (12 user stories)
    └── design.md             # System architecture & design doc
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.12+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Redis | Any (cloud or local) | See env setup below |

### 1. Clone & Navigate

```bash
git clone <your-repo-url>
cd Hack2Skill
```

### 2. Backend Setup

```bash
# Create virtual environment
cd backend
python3 -m venv .venv

# Activate it
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables

Create `backend/.env`:

```env
# === LLM (Required) ===
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# === Redis (Required — for conversation memory) ===
REDIS_HOST=your-redis-host
REDIS_PASSWORD=your-redis-password
REDIS_DB_NAME=0

# === AWS Textract (Optional — OCR currently mocked) ===
# AWS_REGION=ap-south-1
# S3_BUCKET_NAME=your-bucket
# DOCUMENT_INTELLIGENCE_API_KEY=
# DOCUMENT_INTELLIGENCE_ENDPOINT=
```

> **Getting a Gemini API Key:** Go to [Google AI Studio](https://aistudio.google.com/apikey) → Create API Key.
>
> **Getting Redis:** Use [Redis Cloud](https://redis.io/try-free/) free tier (30MB), or run locally via `docker run -p 6379:6379 redis`.

### 4. Frontend Setup

```bash
cd ../frontend
npm install
```

### 5. Run

Open **two terminals**:

```bash
# Terminal 1 — Backend (port 8000)
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# Terminal 2 — Frontend (port 5173)  
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## ☁️ AWS Deployment (Amplify + App Runner)

This project consists of two separately deployed services that need to be connected:
- **Frontend**: AWS Amplify Hosting (React SPA)
- **Backend**: AWS App Runner (FastAPI API)

### Step 1: Deploy Backend on AWS App Runner

This repo includes [apprunner.yaml](apprunner.yaml) for source-code deployment (no Docker required).

**In AWS App Runner Console:**

1. **Create Service** → **Source code repository**
2. Connect this GitHub repo and select branch (e.g., `main`)
3. **Configuration**: Select **Use a configuration file** → `apprunner.yaml`
4. **Add Environment Variables** (in App Runner console):
   ```
   AWS_ACCESS_KEY_ID=<your-aws-key>
   AWS_SECRET_ACCESS_KEY=<your-aws-secret>
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=<your-s3-bucket>
   REDIS_HOST=<your-redis-host>
   REDIS_PORT=6379
   REDIS_PASSWORD=<your-redis-password>
   REDIS_DB_NAME=0
   GEMINI_API_KEY=<your-gemini-key>
   CORS_ORIGINS=*
   ```
   > **Note:** Update `CORS_ORIGINS` after frontend deployment (Step 3)

5. **Deploy** and wait for service to be running

6. **Copy the App Runner URL** (looks like: `https://xxxxx.us-east-1.awsapprunner.com`)

---

### Step 2: Deploy Frontend on AWS Amplify

This repo includes [frontend/amplify.yml](frontend/amplify.yml) for Amplify Hosting.

**In AWS Amplify Console:**

1. **New App** → **Host web app** → Connect repository
2. Select this GitHub repo and branch (e.g., `main`)
3. **Build settings**: Amplify auto-detects `amplify.yml` in frontend/
4. **Add Environment Variables**:
   ```
   VITE_COGNITO_USER_POOL_ID=<your-cognito-pool-id>
   VITE_COGNITO_CLIENT_ID=<your-cognito-client-id>
   VITE_COGNITO_REGION=us-east-1
   VITE_API_BASE_URL=<your-app-runner-url-from-step-1>
   ```
   > **Important:** Use the App Runner URL from Step 1 as `VITE_API_BASE_URL`

5. **Save and deploy**

6. **Copy the Amplify URL** (looks like: `https://main.xxxxx.amplifyapp.com`)

---

### Step 3: Connect Frontend ↔ Backend

**Update CORS in Backend:**

1. Go back to **App Runner** → Your service → **Configuration** → **Environment Variables**
2. Update `CORS_ORIGINS` to your Amplify URL:
   ```
   CORS_ORIGINS=https://main.xxxxx.amplifyapp.com
   ```
3. **Redeploy** the App Runner service

**Verify Connection:**

1. Open your Amplify URL in the browser
2. Create a new session and send a test message
3. Check browser DevTools → Network tab → API calls should hit your App Runner URL
4. Check App Runner logs for incoming requests

---

### Troubleshooting

| Issue | Solution |
|---|---|
| CORS errors | Ensure `CORS_ORIGINS` in App Runner matches exact Amplify URL (no trailing slash) |
| API 404 errors | Verify `VITE_API_BASE_URL` doesn't have `/api` suffix (frontend adds it) |
| Builds fail | Check environment variable names match exactly (prefixes: `VITE_` for frontend) |
| Backend crashes | Review App Runner logs → Configuration → Logs for Python errors |

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/session` | Create a new session |
| `GET` | `/api/session/{id}` | Get current session state |
| `POST` | `/api/chat` | Send message to active agent |
| `POST` | `/api/upload` | Upload document (PDF/image) for OCR |
| `POST` | `/api/panic` | Emergency wipe — deletes all session data |
| `GET` | `/api/health` | Health check |

**Example — Send a message:**
```bash
# Create session
SESSION=$(curl -s -X POST http://localhost:8000/api/session | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

# Chat
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"message\": \"I have been evicted from my house\"}" | python3 -m json.tool
```

---

## 🖥️ CLI Test (No Frontend Required)

You can test the Legal Agent directly from the terminal:

```bash
cd backend
source .venv/bin/activate
python test_cli.py
```

This starts an interactive chat with a mocked triage state (illegal eviction scenario). Type your messages and see the agent respond.

---

## 🔑 Key Features (MVP)

| Feature | Status |
|---|---|
| Trauma-informed chat UI | ✅ Built |
| Legal Agent (eviction workflow) | ✅ Working |
| Panic Button (instant session wipe) | ✅ Built |
| Conversation Memory (Redis + LLM summarization) | ✅ Working |
| Document Upload UI | ✅ Built |
| OCR (AWS Textract) | 🔧 Built, not wired |
| RAG Pipeline | 📋 Planned |
| Shelter Agent | 📋 Planned |
| PDF Draft Generation | 📋 Planned |
| Multilingual Support | 📋 UI ready, backend pending |

---

## 🛡️ Privacy & Safety

- **Panic Button**: One-click wipes all data and redirects to Google
- **In-memory sessions**: No persistent storage by default
- **Redis TTL**: Conversation memory auto-expires
- **No cloud PII**: Documents processed locally (when OCR is wired)

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 7, Vanilla CSS |
| Backend | FastAPI, Python 3.12 |
| LLM | Gemini 2.5 Flash (via OpenAI-compatible API + Instructor) |
| Memory | Redis (sliding window + L2 summarization) |
| OCR | AWS Textract |
| Models | Pydantic v2 |
| Templates | Jinja2 |

---

## 📄 License

This project is part of the Hack2Skill hackathon submission.
