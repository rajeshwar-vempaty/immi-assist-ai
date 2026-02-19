# 🇺🇸 ImmiAssist AI — Intelligent Immigration Assistant

An AI-powered platform that provides affordable, accurate, 24/7 immigration guidance using multi-LLM orchestration and RAG (Retrieval-Augmented Generation) over official USCIS sources.

## 🏗️ Architecture

```
User Query → Intent Classifier (Gemini Flash) → Router
                                                   │
                    ┌──────────────┬────────────────┼──────────────┐
                    ▼              ▼                ▼              ▼
              Policy Q&A    Doc Checklist    Timeline Est.    RFE Helper
              (Claude)      (Gemini Pro)     (Gemini Pro)     (Claude)
                    │              │                │              │
                    └──────────────┴────────────────┴──────────────┘
                                        │
                                   RAG Layer
                              (ChromaDB + Embeddings)
                                        │
                              Safety & Disclaimer Layer
                                        │
                                   Response + Citations
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- API Keys: OpenAI, Anthropic, Google Gemini

### 1. Clone & Setup Environment
```bash
cd immi-assist-ai
cp .env.example .env
# Add your API keys to .env
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Initialize Knowledge Base
```bash
# Scrape USCIS data and build vector store
python -m scripts.ingest_uscis_data
```

### 4. Run Backend
```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Run Frontend
```bash
cd frontend
npm install
npm run dev
```

### 6. Open
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

## 📁 Project Structure
```
immi-assist-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── api/                  # API route handlers
│   │   │   ├── chat.py           # Chat endpoint
│   │   │   ├── checklist.py      # Document checklist endpoint
│   │   │   ├── timeline.py       # Processing timeline endpoint
│   │   │   └── rfe.py            # RFE analysis endpoint
│   │   ├── core/                 # Core configuration
│   │   │   ├── config.py         # Settings & env vars
│   │   │   ├── llm_router.py     # Multi-LLM routing logic
│   │   │   └── prompts.py        # System prompts for each LLM
│   │   ├── services/             # Business logic
│   │   │   ├── rag_service.py    # RAG retrieval & generation
│   │   │   ├── checklist_service.py
│   │   │   ├── timeline_service.py
│   │   │   └── rfe_service.py
│   │   ├── models/               # Database models
│   │   │   └── models.py
│   │   ├── schemas/              # Pydantic schemas
│   │   │   └── schemas.py
│   │   └── utils/                # Helpers
│   │       ├── disclaimer.py     # Legal disclaimer injection
│   │       └── citations.py      # Source citation formatter
│   ├── data/
│   │   ├── scrapers/             # USCIS data scrapers
│   │   │   ├── uscis_policy.py
│   │   │   ├── uscis_forms.py
│   │   │   └── processing_times.py
│   │   └── embeddings/           # Vector store management
│   │       └── ingest.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                     # Next.js / React frontend
├── scripts/                      # Utility scripts
│   └── ingest_uscis_data.py
├── docs/                         # Documentation
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🔑 Features (MVP)
- **Immigration Q&A** — RAG-powered answers with USCIS source citations
- **Document Checklist** — Personalized checklists by visa type
- **Timeline Estimator** — Processing time estimates with historical comparison
- **RFE Response Helper** — Analyze RFE notices and generate response outlines

## ⚖️ Legal Disclaimer
This tool provides informational guidance only and does not constitute legal advice. Always consult a licensed immigration attorney for your specific case.

## 📄 License
MIT
