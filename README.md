# ⚖️ Sahayak — Last Mile Justice Navigator

An AI-powered legal crisis navigator that helps individuals facing **illegal eviction**, **domestic violence**, and **senior citizen neglect** navigate legal procedures, generate official court-ready documents, and find emergency shelter — all with a privacy-first, trauma-informed approach.

> **Built for the AWS Hackathon.** Four AI agents (Triage → Shelter → Legal → Drafting) orchestrate the entire journey from crisis to court-ready paperwork, powered by **AWS Bedrock** (Llama 3.2 90B) with **Groq** failover.

---

## 🏗️ Architecture

```
Hack2Skill/
├── backend/                      # FastAPI + Multi-Agent System
│   ├── agents/
│   │   ├── triage_agent.py       # Crisis profiling & needs assessment
│   │   ├── shelter_agent.py      # Shelter search with geocoding
│   │   ├── legal_agent.py        # Legal workflow (3 crisis categories)
│   │   └── drafting_agent.py     # PDF generation via fpdf2
│   ├── core/
│   │   ├── orchestrator.py       # Agent routing, handoffs & chaining
│   │   ├── memory.py             # Redis memory + DynamoDB L2 summarization
│   │   └── bedrock_client.py     # AWS Bedrock Converse API wrapper
│   ├── services/
│   │   ├── llm_service.py        # LLM gateway (Bedrock primary → Groq fallback)
│   │   ├── ocr_service.py        # AWS Textract (sync images + async PDFs via S3)
│   │   ├── rag_service.py        # RAG pipeline (Cohere embeddings + ChromaDB)
│   │   ├── shelter_service.py    # Shelter matching with geospatial search
│   │   ├── chat_storage_service.py   # DynamoDB chat persistence
│   │   └── draft_storage_service.py  # S3 draft storage + streaming download
│   ├── models/                   # Pydantic v2 data models
│   │   ├── session.py            # Global session state
│   │   ├── triage.py             # Triage state (name, age, phone, crisis category)
│   │   ├── legal.py              # Legal state, draft payloads (age + phone)
│   │   ├── shelter.py            # Shelter profiles & workflow
│   │   ├── drafting.py           # Draft generation state
│   │   └── enums.py              # Crisis categories, document types
│   ├── prompts/                  # Jinja2 system prompts (per agent, per category)
│   ├── templates/                # 12 legal document HTML → PDF templates
│   ├── config/
│   │   ├── config.py             # Pydantic settings (env-driven)
│   │   └── translations.py       # Multi-language response strings
│   └── main.py                   # FastAPI server & all API endpoints
├── frontend/                     # Vite 7 + React 19 SPA
│   └── src/
│       ├── components/
│       │   ├── ChatApp.jsx       # Main chat layout + right sidebar
│       │   ├── ChatWindow.jsx    # Message list + auto-scroll
│       │   ├── InputBar.jsx      # Text input + voice (Web Speech API) + file upload
│       │   ├── MessageBubble.jsx # Markdown links + fetch-based PDF download
│       │   ├── PanicButton.jsx   # Emergency session wipe → redirect to Google
│       │   ├── Sidebar.jsx       # Left nav (language, new session)
│       │   ├── LandingPage.jsx   # Landing page with auth
│       │   └── LoginPage.jsx / SignupPage.jsx / ForgotPasswordPage.jsx
│       ├── hooks/
│       │   ├── useChat.js        # Chat + upload state management
│       │   ├── useAuth.jsx       # AWS Cognito auth (anonymous fallback)
│       │   └── useLanguage.jsx   # i18n context (EN/HI/TA/BN)
│       └── utils/
│           ├── api.js            # REST client + downloadDraft() via fetch→blob
│           └── translations.js   # UI string translations
└── documentation/
    ├── requirements.md           # 12 user stories
    └── design.md                 # System architecture & design doc
```

---

## 🤖 Multi-Agent Pipeline

```
User Message
     │
     ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   TRIAGE    │────▶│   SHELTER   │────▶│    LEGAL    │────▶│  DRAFTING   │
│   Agent     │     │   Agent     │     │   Agent     │     │   Agent     │
│             │     │             │     │             │     │             │
│ • Profile   │     │ • Geocode   │     │ • OCR docs  │     │ • Render    │
│ • Classify  │     │ • DB search │     │ • RAG laws  │     │   Jinja2    │
│ • Urgency   │     │ • Present   │     │ • Gather    │     │ • fpdf2 PDF │
│ • Name/Age/ │     │   options   │     │   facts     │     │ • S3 upload │
│   Phone     │     │ • Consent   │     │ • Consent   │     │ • Download  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Supported Crisis Categories:**
| Category | Legal Drafts Generated |
|---|---|
| **Illegal Eviction** | Police Complaint (BNS 126), Civil Injunction Petition, KSLSA Legal Aid |
| **Domestic Violence** | Safety Plan, DIR Form I, Section 12 Petition, KSLSA Legal Aid |
| **Senior Citizen Neglect** | Tribunal Complaint (2007 Act), KSLSA Legal Aid, Police Intimation |

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.12+ |
| Node.js | 18+ |
| Redis | Any (cloud or local) |

### 1. Clone & Setup Backend

```bash
git clone https://github.com/Udit-H/Hack2Skill.git
cd Hack2Skill/backend

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables

Create `backend/.env`:

```env
# === LLM — AWS Bedrock (Primary) ===
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
BEDROCK_MODEL_ID=us.meta.llama3-2-90b-instruct-v1:0

# === LLM — Groq (Fallback) ===
GROQ_API_KEY=your-groq-key
GROQ_MODEL_ID=llama-3.3-70b-versatile

# === Redis (Conversation memory) ===
REDIS_URL=redis://default:password@host:port

# === AWS S3 (Document uploads + draft storage) ===
S3_BUCKET_NAME=your-s3-bucket

# === RAG Pipeline ===
COHERE_API_KEY=your-cohere-key
CHROMA_TENANT=your-tenant
CHROMA_DATABASE=your-database
CHROMA_TOKEN=your-token

# === DynamoDB Tables (auto-created via setup script) ===
DYNAMODB_CHAT_TABLE=sahayak-chat-messages
RAG_CACHE_TABLE=sahayak-rag-cache
DYNAMODB_SUMMARY_TABLE=sahayak-session-summaries
```

### 3. Create DynamoDB Tables

```bash
cd backend
source .venv/bin/activate
python playground/setup_dynamodb.py
```

This creates 3 tables: chat messages, RAG cache (24h TTL), and session summaries.

### 4. Frontend Setup

```bash
cd frontend
npm install
```

Optionally create `frontend/.env` for Cognito auth:
```env
VITE_COGNITO_USER_POOL_ID=your-pool-id
VITE_COGNITO_CLIENT_ID=your-client-id
VITE_COGNITO_REGION=us-east-1
VITE_API_BASE_URL=http://localhost:8080
```

> Without Cognito env vars, the app falls back to **anonymous mode** (fully functional).

### 5. Run

```bash
# Terminal 1 — Backend (port 8080)
cd backend && source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Terminal 2 — Frontend (port 5173)
cd frontend
npm run dev
```

Open **http://localhost:5173**.

---

## ☁️ AWS Deployment

| Component | Service | Config File |
|---|---|---|
| **Backend** | AWS App Runner | `apprunner.yaml` |
| **Frontend** | AWS Amplify Hosting | `frontend/amplify.yml` |
| **Auth** | AWS Cognito | via `aws-amplify` SDK |
| **OCR** | AWS Textract | Sync (images) + Async (PDFs via S3) |
| **LLM** | AWS Bedrock | Llama 3.2 90B Instruct |
| **Storage** | DynamoDB + S3 | Chat, RAG cache, summaries, drafts |
| **Memory** | Redis (Upstash/ElastiCache) | Sliding window + L2 summarization |

### Deploy Backend (App Runner)

1. **Create Service** → Source code repository → connect this repo
2. Select **Use a configuration file** → `apprunner.yaml`
3. Add environment variables (same as `.env` above)
4. Deploy — backend runs on port 8080

### Deploy Frontend (Amplify)

1. **New App** → Host web app → connect this repo
2. Amplify auto-detects `frontend/amplify.yml`
3. Add environment variables:
   - `VITE_API_BASE_URL` = App Runner URL from above
   - `VITE_COGNITO_USER_POOL_ID`, `VITE_COGNITO_CLIENT_ID`, `VITE_COGNITO_REGION`
4. Deploy

### Connect Frontend ↔ Backend

Update `CORS_ORIGINS` in App Runner env to your Amplify URL.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/session` | Create a new session |
| `GET` | `/api/session/{id}` | Get session state |
| `POST` | `/api/chat` | Send message to active agent |
| `POST` | `/api/upload` | Upload document (PDF/image) for OCR |
| `GET` | `/api/drafts/{session_id}/{filename}` | Download generated PDF |
| `POST` | `/api/panic` | Emergency wipe — delete all session data |
| `POST` | `/api/sessions/list` | List user sessions |
| `POST` | `/api/sessions/load` | Load existing session |
| `GET` | `/api/chat-history/{session_id}` | Retrieve chat history |
| `GET` | `/api/health` | Health check |

---

## 🔑 Key Features

| Feature | Status |
|---|---|
| **4-Agent Pipeline** (Triage → Shelter → Legal → Drafting) | ✅ |
| **3 Crisis Categories** (Eviction, DV, Senior Citizen) | ✅ |
| **AWS Bedrock LLM** (Llama 3.2 90B) + Groq fallback | ✅ |
| **AWS Textract OCR** (sync images + async PDFs) | ✅ |
| **Document Summary** (upload → extract → summarize to user) | ✅ |
| **RAG Pipeline** (Cohere + ChromaDB, 20 legal knowledge docs) | ✅ |
| **RAG Cache** (DynamoDB, SHA-256 hash, 24h TTL) | ✅ |
| **12 Legal Document Templates** (Jinja2 → fpdf2 PDF) | ✅ |
| **PDF Download** (fetch → blob → browser save-as) | ✅ |
| **Shelter Search** (DynamoDB geospatial + Nominatim geocoding) | ✅ |
| **Conversation Memory** (Redis sliding window + DynamoDB L2) | ✅ |
| **Multi-session Support** (DynamoDB chat persistence) | ✅ |
| **Voice Input** (Web Speech API, 4 languages) | ✅ |
| **Multilingual UI** (English, Hindi, Tamil, Bengali) | ✅ |
| **Panic Button** (instant session wipe → redirect to Google) | ✅ |
| **Age + Phone Collection** (triage → legal → PDF templates) | ✅ |
| **AWS Cognito Auth** (with anonymous fallback) | ✅ |
| **Rate Limiting** (slowapi per-endpoint) | ✅ |
| **Trauma-Informed Design** (dark theme, calming UI) | ✅ |

---

## 🛡️ Privacy & Safety

- **Panic Button**: One-click wipes all session data and redirects to Google
- **Redis TTL**: Conversation memory auto-expires
- **No persistent PII**: Sessions live in memory; DynamoDB stores only chat messages
- **Cognito Auth**: Optional — works fully in anonymous mode
- **Rate Limiting**: Prevents abuse on all endpoints

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite 7, Vanilla CSS, Web Speech API |
| **Backend** | FastAPI, Python 3.12, Pydantic v2 |
| **LLM** | AWS Bedrock (Llama 3.2 90B) → Groq fallback (Llama 3.3 70B) |
| **Structured Output** | Instructor (Groq) + manual JSON schema (Bedrock) |
| **OCR** | AWS Textract (sync + async via S3) |
| **RAG** | Cohere Embed v3 + ChromaDB (cloud) |
| **Memory** | Redis (sliding window) + DynamoDB (L2 summarization) |
| **PDF** | fpdf2 (pure Python, zero native deps) |
| **Storage** | DynamoDB (chat, cache, summaries) + S3 (uploads, drafts) |
| **Auth** | AWS Cognito (via aws-amplify SDK) |
| **Shelter Data** | DynamoDB (geohash-based proximity search) |
| **Templates** | Jinja2 (prompts + legal document HTML) |
| **Deployment** | AWS App Runner (backend) + AWS Amplify (frontend) |

---

## 📄 License

This project is part of the Hack2Skill AWS hackathon submission.
