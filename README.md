# AI Study Companion

Upload a PDF or slide deck, get study material generated from it — structured notes,
flashcards, MCQs, short-answer questions — then sit the quiz, and let the system work out
what you keep getting wrong.

**[Live demo](https://ai-study-companion-neon.vercel.app)** · [API docs](https://ai-study-companion-vkqf.onrender.com/docs)

[![tests](https://github.com/Mnvv08/ai-study-companion/actions/workflows/tests.yml/badge.svg)](https://github.com/Mnvv08/ai-study-companion/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![Postgres](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)

<!-- TODO: replace with a real screenshot of the dashboard before sharing this repo.
     docs/screenshot.png -->

---

## Why this exists

Most AI study tools stop at generation. You upload a chapter, you get twenty flashcards,
and that's the product — the tool has no idea whether you actually learned anything.

The generation here is the easy half. The half worth building is what happens after: every
quiz attempt is stored per question and per topic, so the system can tell you that you are
fine on normalization and losing marks consistently on transaction isolation levels, and
point you back at the specific section of the document that covers it.

Answers are grounded in the uploaded document through retrieval rather than generated from
the model's own knowledge. Ask something the document doesn't cover and the endpoint says
so instead of inventing a plausible answer — which matters more for study material than for
almost anything else, because a confident wrong explanation is worse than no explanation.

---

## What it does

- **Upload PDFs and PowerPoint decks** — layout-aware text extraction via `pdfplumber` and
  `python-pptx`, with validation on extension, size, and file corruption at the edge
- **Structured study notes** — sections, key definitions, and summaries generated from the
  document's actual content
- **Active-recall flashcards** with topic tags, so they can be filtered by weak area
- **Multiple choice questions** with validated answer indices, and **short-answer questions**
  with model answers for side-by-side comparison
- **Grounded Q&A** over one document or across several at once, retrieved from a per-user
  vector store
- **A real quiz engine** — attempts, per-question answers, and scores persisted in Postgres,
  with a full attempt history
- **Weak-topic analytics and revision recommendations** derived from that history, not from
  a fresh prompt to the model
- **Spaced-repetition scheduling** over those topics using SM-2, so the app answers "what
  should I study today" and not just "what am I bad at"
- **A toggleable Hinglish mentor persona** — the same explanations in the register a lot of
  Indian students actually think in, switched on or off per user
- **Per-user rate limiting and response caching**, because LLM calls cost money and students
  click buttons twice

---

## Architecture

```
┌──────────────┐        ┌─────────────────────────────────────────────┐
│  React + Vite │──JWT──▶│  FastAPI                                    │
│  (Vercel)     │◀───────│                                             │
└──────────────┘        │  ┌────────────┐  ┌──────────────────────┐   │
                         │  │ Extraction  │  │ Groq                 │   │
                         │  │ pdfplumber  │  │ llama-3.3-70b        │   │
                         │  │ python-pptx │  │ + embeddings         │   │
                         │  └─────┬──────┘  └──────────┬───────────┘   │
                         │        │                     │               │
                         │        ▼                     ▼               │
                         │  ┌──────────┐         ┌────────────┐        │
                         │  │ ChromaDB  │         │ PostgreSQL │        │
                         │  │ (vectors) │         │ (users,    │        │
                         │  │ per-user  │         │  quizzes,  │        │
                         │  │ namespaced│         │  attempts) │        │
                         │  └──────────┘         └────────────┘        │
                         └─────────────────────────────────────────────┘
```

Two stores, deliberately. Chunk embeddings go to ChromaDB because retrieval is a
similarity problem; users, quizzes, attempts and answers go to Postgres because analytics
over quiz history is a relational problem. Vector databases are bad at "show me this
student's average score per topic over the last month."

**The API key never reaches the browser.** All Groq calls originate server-side. The
frontend holds a JWT and nothing else.

`ALLOWED_ORIGINS` is read from the environment rather than hardcoded, so pointing the API
at a new frontend deployment is a config change on the host, not a code edit and redeploy.

---

## Data model

```
User ──┬── Document ──── (chunks → ChromaDB, namespaced by user)
       │
       ├── QuizAttempt ──── AttemptAnswer ──▶ Question ──▶ Quiz
       │                                        │
       │                                     topic_tag
       │                                        │
       └── TopicReview ◀────────────────────────┘
           (SM-2 state: repetitions, interval, ease, due date)
```

Storing `AttemptAnswer` per question rather than only a final score is what makes the
analytics possible at all. A score of 6/10 tells you nothing actionable; six rows tagged
with the topic each question came from tell you exactly what to revise.

---

## API

All endpoints are served under `/api/v1`. Interactive docs at `/docs`.

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | — | Service status and database connectivity probe |
| `POST` | `/auth/register` | — | Create an account |
| `POST` | `/auth/login` | — | Exchange credentials for a JWT |
| `GET` | `/auth/me` | JWT | Current user |
| `POST` | `/documents/upload` | JWT | Upload and extract a PDF or PPTX |
| `GET` | `/documents/` | JWT | List your documents |
| `GET` | `/documents/{id}` | JWT | Document detail |
| `GET` | `/documents/{id}/status` | JWT | Processing status: pending / processed / failed |
| `DELETE` | `/documents/{id}` | JWT | Delete a document and its vectors |
| `POST` | `/notes/generate` | JWT | Structured study notes |
| `POST` | `/flashcards/generate` | JWT | Topic-tagged flashcards |
| `POST` | `/mcqs/generate` | JWT | MCQs with validated correct indices |
| `POST` | `/short-answer/generate` | JWT | Short-answer questions with model answers |
| `POST` | `/qa/ask` | JWT | Grounded Q&A over one document |
| `POST` | `/qa/ask-multi` | JWT | Grounded Q&A across several documents |
| `GET` | `/quizzes/history` | JWT | Past attempts with scores |
| `GET` | `/quizzes/{id}` | JWT | A single attempt with its questions |
| `POST` | `/quizzes/{id}/submit` | JWT | Submit answers and get graded |
| `GET` | `/analytics/weak-topics` | JWT | Topics ranked by error rate |
| `GET` | `/analytics/recommendations` | JWT | What to revise next, and why |
| `GET` | `/review/due` | JWT | Topics due for review now, most overdue first |
| `GET` | `/review/schedule` | JWT | Every tracked topic with its next review date |
| `GET` | `/users/me/settings` | JWT | Read settings, including persona toggle |
| `PATCH` | `/users/me/settings` | JWT | Update settings |

---

## Running it locally

```bash
cp .env.example .env
cp .env.example backend/.env
```

Add your Groq key to `backend/.env` (free tier is enough — get one at
[console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=gsk_your-key-here
```

Then:

```bash
docker compose up --build
```

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| ChromaDB | http://localhost:8001 |

Stop with `docker compose down`.

---

## Tests

90 tests covering auth, upload and extraction, each generator, the RAG layer, the quiz
engine, analytics, the persona toggle, rate limiting, caching, and the spaced-repetition
scheduler. They run on every push
and pull request via GitHub Actions.

```bash
cd backend
pytest -q
```

The suite never calls Groq or touches a real database, but `pydantic-settings` still
requires the config fields to be present — the app is designed to crash at startup on
missing configuration rather than fail confusingly on the first request, and the test
environment respects that.

---

## Honest limitations

- Extraction quality is bounded by the source file. Scanned PDFs without a text layer
  produce nothing useful — there is no OCR step.
- Weak-topic analytics need a handful of completed quizzes before the output means
  anything. With two attempts it is describing noise.
- Topic labels come from the model at generation time, so the same concept can occasionally
  land under two slightly different labels and split its own statistics.
- Scheduling needs a few completed quizzes per topic before the intervals mean anything.
  SM-2 was designed for flashcards reviewed daily, and a topic seen twice is still being
  scheduled mostly on its defaults.
- Migrations are managed by Alembic, but the free Render tier has no shell or pre-deploy
  hook, so they are applied manually from a laptop rather than automatically on deploy.
- The free-tier backend host sleeps when idle, so the first request after a quiet period
  can take a while.
- This is a learning and portfolio project, not a product. Don't put anything confidential
  in it.

---

## Stack

**Backend** — Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, ChromaDB, pdfplumber,
python-pptx, slowapi, JWT via python-jose, passlib/bcrypt
**Frontend** — React 18, Vite, Tailwind CSS, axios
**AI** — Groq (`llama-3.3-70b-versatile` for generation, `nomic-embed-text-v1_5` for embeddings)
**Infra** — Docker Compose locally, Vercel for the frontend, GitHub Actions for CI

---

## Roadmap

- [x] Phase 0 — Scaffold, Docker Compose, health checks
- [x] Phase 1 — JWT auth, PDF upload, layout-aware extraction, RAG Q&A, notes
- [x] Phase 2 — Flashcards, MCQs, short-answer generation
- [x] Phase 3 — Quiz engine with attempts and scores in PostgreSQL
- [x] Phase 4 — Weak-topic detection from quiz history
- [x] Phase 5 — Revision recommendations
- [x] Phase 6 — PPTX and multi-document support
- [x] Phase 7 — Hinglish student-mentor persona
- [x] Phase 8 — Rate limiting, caching, deployment
- [x] Alembic migrations replacing `create_all()`
- [x] Spaced-repetition scheduling on top of weak-topic analytics
- [ ] OCR fallback for scanned PDFs

---

## License

MIT.

Built by [@Mnvv08](https://github.com/Mnvv08).
