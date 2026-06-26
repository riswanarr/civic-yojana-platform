# Government Schemes Discovery Platform

AI-powered government schemes discovery platform scaffold for a solo final-year project.

This repository contains only project setup and placeholder modules. It does not include authentication, database schema, Supabase integration, RAG logic, API business logic, mock data, or feature implementations.

## Tech Stack

Frontend:
- React
- Vite
- TypeScript
- TailwindCSS
- shadcn/ui
- Zustand
- React Router

Backend:
- FastAPI
- Python
- Supabase
- LangChain
- Gemini API
- pgvector

## Project Structure

```txt
.
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── lib/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── store/
│   │   └── types/
│   └── package.json
└── backend/
    ├── app/
    │   ├── api/
    │   ├── database/
    │   ├── models/
    │   ├── rag/
    │   ├── schemas/
    │   ├── services/
    │   └── utils/
    ├── scripts/
    ├── tests/
    └── requirements.txt
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Default local URL:

```txt
http://localhost:5173
```

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Default local URL:

```txt
http://localhost:8000
```

API docs:

```txt
http://localhost:8000/docs
```

## Environment Files

Copy the examples before running each app:

```bash
cp frontend/.env.example frontend/.env
cp backend/.env.example backend/.env
```

Fill in real values when implementing integrations.

