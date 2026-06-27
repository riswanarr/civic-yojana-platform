# civic-योजना

AI-powered platform for discovering, tracking, and receiving updates about Indian government schemes, scholarships, internships, and opportunities.

civic-योजना helps citizens discover relevant opportunities, receive personalized recommendations, save schemes, track applications, and receive timely notifications about new opportunities and deadlines.

## Features

* Government Scheme and Opportunity Discovery
* Personalized AI Recommendations
* Chat Assistant for Scheme Queries
* Saved Schemes and Application Tracking
* Notifications and Deadline Alerts
* Live Opportunity Updates and Sync Engine
* Profile-Based Matching

## Tech Stack

### Frontend

* React
* Vite
* TypeScript
* TailwindCSS
* shadcn/ui
* Zustand
* React Router

### Backend

* FastAPI
* Python
* Supabase
* LangChain
* Gemini API
* pgvector

## Architecture

Sources → Parsers → Sync Engine → Database → Notifications → Frontend

## Project Status

Actively under development.

Upcoming:

* Real source integrations
* Automatic sync scheduler
* Multilingual support
* Voice interactions


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

