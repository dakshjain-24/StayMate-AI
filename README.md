# StayMate AI — Agentic Hotel Operations Assistant

StayMate AI is a portfolio project that combines an AI hotel receptionist with a lightweight staff operations dashboard. The receptionist can answer hotel questions using RAG, check room availability, create/cancel bookings, and create housekeeping or maintenance requests through structured tool calls.

The codebase is intentionally kept readable and interview-friendly: one backend service, clear domain modules, a real SQL database, and a LangGraph workflow that is easy to draw on a whiteboard.

## Features

- LangGraph intent routing for FAQ, booking, service, and general requests
- RAG over hotel policies, amenities, timings, and menu information
- PostgreSQL + pgvector for structured hotel data and embeddings
- Room availability checks with overlapping-booking validation
- Booking creation and cancellation through backend tools
- Housekeeping, maintenance, room-service, and general service requests
- Conversational state using a LangGraph checkpointer
- React staff dashboard for rooms, bookings, and service requests
- Evaluation script for intent-routing accuracy and RAG source hit rate

## Tech stack

**Frontend:** React.js, Vite, CSS

**Backend:** Python, FastAPI, SQLAlchemy

**AI:** LangChain, LangGraph, OpenAI-compatible LangChain integration, RAG, tool calling

**Database:** PostgreSQL, pgvector

**Infrastructure:** Docker, Docker Compose

## Repository structure

```text
staymate-ai/
├── backend/
│   ├── app/
│   │   ├── agent/          # LangGraph workflow
│   │   ├── api/            # FastAPI routes
│   │   ├── core/           # settings
│   │   ├── db/             # engine/session
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # request/response models
│   │   ├── services/       # business logic and RAG
│   │   └── tools/          # LangChain tools used by the agent
│   ├── evaluate.py
│   ├── seed.py
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── services/
├── knowledge/              # sample hotel knowledge base
├── evaluation/             # small evaluation dataset
├── ARCHITECTURE.md
└── docker-compose.yml
```

## 1. Prerequisites

Install:

- Python 3.11+
- Node.js 20+
- PostgreSQL with pgvector, or Docker Desktop
- an OpenAI API key (or adapt the model/embedding classes to another provider)

## 2. Local setup

### Database

The easiest option is to start only PostgreSQL through Docker:

```bash
docker compose up -d db
```

### Backend

```bash
cd backend
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your environment file:

```bash
cp .env.example .env
```

On Windows, copy `.env.example` to `.env` manually if `cp` is not available.

Set at least:

```env
OPENAI_API_KEY=your_key_here
DATABASE_URL=postgresql+psycopg://staymate:staymate@localhost:5432/staymate
```

Seed demo hotel data and embed the knowledge base:

```bash
python seed.py
```

Run the API:

```bash
uvicorn app.main:app --reload
```

FastAPI docs will be available at:

```text
http://localhost:8000/docs
```

### Frontend

Open another terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open:

```text
http://localhost:5173
```

## 3. Full Docker setup

First create `backend/.env` from `backend/.env.example` and add your API key.

Then:

```bash
docker compose up --build -d
```

Seed the database after the backend container is running:

```bash
docker compose exec backend python seed.py
```

Open the frontend at `http://localhost:5173`.

## Demo prompts

Try these in the AI Receptionist tab:

```text
What time does breakfast end?
```

```text
Do you have a deluxe room from 2026-10-04 to 2026-10-07?
```

```text
I want to book that deluxe room. My name is Alex Sharma and my email is alex@example.com.
```

```text
Please send two extra towels to room 301.
```

```text
The AC in room 301 isn't cooling properly. Please report it.
```

## Evaluation

After seeding the database:

```bash
cd backend
python evaluate.py
```

The script reports:

- intent-routing accuracy on the included query set
- RAG source hit rate@3

Expand `evaluation/cases.json` before quoting numbers on your resume. A larger manually-reviewed set is more defensible than a tiny demo set.

## Author

Daksh Jain
