# 🎓 AI Study Companion

An AI-powered study platform where students can upload PDF/PPT study materials and get AI-generated notes, flashcards, MCQs, Q&A, quiz tracking, and personalized revision recommendations.

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + Tailwind CSS |
| Backend | Python + FastAPI |
| AI | OpenAI LLM + Embeddings + RAG |
| Vector DB | ChromaDB |
| Relational DB | PostgreSQL |
| Auth | JWT |
| Infra | Docker + Docker Compose |

## 🚀 Planned Features

- [x] Phase 0 — Repo scaffold, Docker Compose, health check
- [ ] Phase 1 — JWT auth, PDF upload, text extraction, RAG Q&A, notes generation
- [ ] Phase 2 — Flashcards, MCQs, short-answer questions
- [ ] Phase 3 — Quiz engine + score tracking
- [ ] Phase 4 — Weak topic detection
- [ ] Phase 5 — Revision recommendations
- [ ] Phase 6 — PPT + multi-document support
- [ ] Phase 7 — Hinglish student-mentor persona
- [ ] Phase 8 — Rate limiting, caching, deployment

## ⚡ Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/Mnvv08/ai-study-companion.git
cd ai-study-companion

# 2. Set up environment variables
cd backend
cp .env.example .env
# Edit .env with your real values (API keys, DB password, etc.)

# 3. Start everything
docker compose up --build
```

### Verify it's running

| URL | Expected |
|---|---|
| `http://localhost:8000/` | Welcome JSON |
| `http://localhost:8000/api/v1/health` | `{"status": "ok", "database": "connected"}` |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:5173` | React frontend |

## 📁 Project Structure

```
ai-study-companion/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── core/            # Config (pydantic-settings)
│   │   ├── api/v1/          # Route handlers
│   │   ├── db/              # SQLAlchemy session + base
│   │   ├── models/          # DB models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example         # Copy to .env — never commit real .env!
├── frontend/
│   ├── src/
│   ├── vite.config.js
│   └── Dockerfile
└── docker-compose.yml
```

## 🔐 Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — JWT signing key (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
- `OPENAI_API_KEY` — Your OpenAI API key

> ⚠️ **Never commit your `.env` file.** It's in `.gitignore`.

---

Built with ❤️ by [@Mnvv08](https://github.com/Mnvv08)
