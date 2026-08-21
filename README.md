# 🎓 AI Study Companion

An AI-powered study platform where students can upload PDF study materials and generate structured study notes, active-recall flashcards, MCQs, short-answer exam questions, and ask questions about their material with grounded RAG Q&A.

---

## 🛠️ Tech Stack

| Layer | Technology | Description |
|---|---|---|
| **Frontend** | React 18 + Vite + Tailwind CSS | Fast dev server, responsive dark UI, toast alerts |
| **Backend** | Python 3.11 + FastAPI + Pydantic v2 | High-performance asynchronous REST API |
| **AI / LLM** | OpenAI API (`gpt-4o-mini`, `text-embedding-3-small`) | Fast, cost-effective inference & vector embeddings |
| **Vector DB** | ChromaDB | Open-source embedding storage with cosine distance search |
| **Relational DB** | PostgreSQL 15 | Users, document metadata, and future quiz performance tracking |
| **Auth & Security** | JWT (JSON Web Tokens) + Passlib / Bcrypt | Stateless Bearer authentication & secure salted hashing |
| **Infra** | Docker & Docker Compose | Containerized local orchestration with live hot-reloading |

---

## 🚀 Development Roadmap & Completed Features

- [x] **Phase 0 — Repo scaffold, Docker Compose, health check**
  - Multi-container architecture (`postgres`, `backend`, `frontend`, `chromadb`).
  - Centralized `pydantic-settings` configuration with `.env.example`.
  - Live health check endpoint (`GET /api/v1/health`) probing DB connection (`SELECT 1`).
- [x] **Phase 1 (MVP) — JWT Auth, PDF Upload, Layout Text Extraction, RAG Q&A, Notes Generation**
  - User registration & login with password hashing and JWT access tokens.
  - Edge validation on upload (`.pdf` only, size limits, corruption detection).
  - Layout-aware PDF text extraction with `pdfplumber`.
  - Recursive text chunking, OpenAI embeddings, and multi-tenant ChromaDB storage.
  - Grounded RAG Question Answering (`POST /qa/ask`) refusing hallucinations.
  - Structured exam-ready notes generation (`POST /notes/generate`).
- [x] **Phase 2 — AI Study Artifacts Generation**
  - Active-recall flashcards (`POST /flashcards/generate`) with topic tags.
  - 4-Option Multiple Choice Questions (`POST /mcqs/generate`) with `correct_index` range validation.
  - Short-answer exam questions (`POST /short-answer/generate`) with 1-3 sentence model answers.
- [ ] **Phase 3 — Quiz Engine + Score Tracking in PostgreSQL**
- [ ] **Phase 4 — Weak Topic Detection (Analytics from Quiz History)**
- [ ] **Phase 5 — Smart Revision Recommendations**
- [ ] **Phase 6 — PPTX + Multi-Document Support**
- [ ] **Phase 7 — Hinglish Student-Mentor Persona Layer**
- [ ] **Phase 8 — Rate Limiting, Caching, & Production Deployment**

---

## ⚡ Quick Start: How to Run the Project

### 1. Configure Environment Variables
Copy `.env.example` to `.env` and `backend/.env`:
```bash
cp .env.example .env
cp .env.example backend/.env
```
Open `backend/.env` and insert your real OpenAI API Key:
```ini
OPENAI_API_KEY=sk-your-openai-key-here
```

### 2. Start Services with Docker Compose
```bash
docker compose up --build
```

### 3. Open Services in Your Browser
- 📖 **Interactive Swagger UI (API Docs):** [http://localhost:8000/docs](http://localhost:8000/docs)
- 📚 **Alternative ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- 💻 **Frontend Live Dashboard:** [http://localhost:5173](http://localhost:5173)
- 🗄️ **ChromaDB Vector Store:** [http://localhost:8001](http://localhost:8001)

---

## 🧪 API Endpoints Overview

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | Public | System status and PostgreSQL connectivity probe |
| `POST` | `/api/v1/auth/register` | Public | Register a new student user |
| `POST` | `/api/v1/auth/login` | Public | Authenticate and obtain JWT access token |
| `POST` | `/documents/upload` | Bearer JWT | Upload and extract a PDF study document |
| `GET` | `/documents/{id}/status` | Bearer JWT | Check processing status (`pending`, `processed`, `failed`) |
| `POST` | `/qa/ask` | Bearer JWT | Ask a question about an uploaded document (RAG Q&A) |
| `POST` | `/notes/generate` | Bearer JWT | Generate structured exam notes with key definitions |
| `POST` | `/flashcards/generate` | Bearer JWT | Generate active-recall flashcards with topic labels |
| `POST` | `/mcqs/generate` | Bearer JWT | Generate 4-option MCQs with validated correct indices |
| `POST` | `/short-answer/generate` | Bearer JWT | Generate conceptual short-answer exam questions |

---

## 🛑 Stopping the System
```bash
docker compose down
```

---

Built with ❤️ by [@Mnvv08](https://github.com/Mnvv08)
