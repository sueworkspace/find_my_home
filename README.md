# pointless

A fullstack web application built with React and FastAPI.

## Tech Stack

- **Frontend**: React 18, Vite, React Router
- **Backend**: Python 3.12, FastAPI, SQLAlchemy
- **Infrastructure**: Docker, Docker Compose

## Getting Started

### Prerequisites

- Docker & Docker Compose (recommended)
- Or: Node.js 20+, Python 3.12+

### Run with Docker

```bash
cp .env.example .env
docker compose up
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Run Locally

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
pointless/
├── backend/
│   ├── app/
│   │   ├── api/         # API routes
│   │   ├── core/        # Configuration
│   │   ├── models/      # Database models
│   │   └── schemas/     # Pydantic schemas
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/  # Reusable components
│   │   ├── hooks/       # Custom hooks
│   │   ├── pages/       # Page components
│   │   └── styles/      # CSS styles
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```
