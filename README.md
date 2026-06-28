# Lab-Grader 🧪

> **Automatic Test Case Generation and Comprehensive Evaluation of C Programming Assignments**

Lab-Grader is an academic web platform that automates the full evaluation lifecycle of C programming assignments in university laboratory courses. Professors upload a reference solution — the system generates test cases automatically, students submit their code before the deadline, and the platform compiles, executes, and grades every submission without manual intervention. Each student receives an individualised evaluation report with a score out of 20, per-test results, static analysis observations, and structured feedback.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running the Platform](#running-the-platform)
- [Building the Sandbox Image](#building-the-sandbox-image)
- [Project Structure](#project-structure)
- [User Roles](#user-roles)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- 🔄 **Automatic test case generation** from a professor's C reference solution
- 🔬 **Hybrid evaluation** — static analysis (pycparser AST) + dynamic black-box execution (Docker + GCC)
- 🛡️ **Secure sandboxed execution** — isolated Docker containers with strict memory, CPU, and network limits
- 📊 **Scoring out of 20** — weighted test cases, late penalty, per-test breakdown
- 💬 **Individualised multilayer feedback** — rule-based diagnostics + optional Claude API suggestions
- 🔔 **Real-time notifications** — students notified automatically upon evaluation completion
- 📅 **Deadline-based evaluation** — all submissions evaluated automatically when the deadline expires
- 👩‍🏫 **Professor dashboard** — submission statistics, leaderboard, per-student score tracking
- 🎓 **Student dashboard** — recent submissions, upcoming deadlines, score history
- 🔁 **Solution replacement** — students can replace submissions before the deadline
- 📁 **Multi-file support** — configurable maximum files per assignment
- 🤖 **Claude API fallback** — AI-assisted test generation and feedback enrichment

---

## Architecture

```
┌─────────────────────────────────────────────┐
│           Client Layer                      │
│   React + Vite + Tailwind + Zustand         │
└────────────────────┬────────────────────────┘
                     │ HTTP / REST
┌────────────────────▼────────────────────────┐
│           Application Layer                 │
│   FastAPI + Pydantic + SQLAlchemy + JWT     │
└────────────────────┬────────────────────────┘
                     │ Celery Queue (Redis)
┌────────────────────▼────────────────────────┐
│        Service & Analysis Layer             │
│  Evaluator + Test Generator + Feedback      │
│  Static Analysis (pycparser)                │
└────────────────────┬────────────────────────┘
                     │ Docker SDK
┌────────────────────▼────────────────────────┐
│           Execution Layer                   │
│   Docker Sandbox + GCC + Celery Workers     │
└────────────────────┬────────────────────────┘
                     │ Read / Write
┌────────────────────▼────────────────────────┐
│             Storage Layer                   │
│   PostgreSQL + Redis + File System          │
└─────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Zustand, Axios, React Query |
| Backend | FastAPI, SQLAlchemy (async), Pydantic, python-jose (JWT) |
| Workers | Celery, Redis, Celery Beat |
| Execution | Docker, GCC (C11), pycparser |
| AI Layer | Anthropic Claude API (optional) |
| Database | PostgreSQL 15, JSONB columns |
| DevOps | Docker Compose, bind-mount volumes |

---

## Prerequisites

Make sure the following are installed on your machine before starting:

| Tool | Version | Download |
|---|---|---|
| Docker Desktop | 24+ | https://www.docker.com/products/docker-desktop |
| Node.js | 20+ | https://nodejs.org |
| Git | Any | https://git-scm.com |

> **Windows users:** Enable Docker Desktop → Settings → General → *Expose daemon on tcp://localhost:2375 without TLS*

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/c-tp-grader.git
cd c-tp-grader
```

### 2. Create the uploads directory

```bash
# Linux / macOS
mkdir -p uploads

# Windows
mkdir uploads
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set your values (see [Environment Variables](#environment-variables)).

### 4. Build the sandbox image

```bash
# Linux / macOS
cd backend/sandbox
docker build --platform linux/amd64 --no-cache -f Dockerfile.sandbox -t c-sandbox:latest .
cd ../..

# Windows (PowerShell)
cd backend\sandbox
docker build --platform linux/amd64 --no-cache -f Dockerfile.sandbox -t c-sandbox:latest .
cd ..\..
```

Verify the image:

```bash
docker images | grep sandbox
docker run --rm --entrypoint="" c-sandbox:latest gcc --version
```

### 5. Start all services

```bash
docker compose up --build -d
```

### 6. Open the platform

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Flower (task monitor) | http://localhost:5555 |

> Flower credentials: **admin / grader123**

---

## Environment Variables

Create a `.env` file in the project root using this template:

```env
# ── Application ──────────────────────────────────────────────
APP_ENV=development
SECRET_KEY=your-secret-key-minimum-32-characters-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ── Database ──────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://grader:grader123@postgres:5432/graderdb
SYNC_DATABASE_URL=postgresql://grader:grader123@postgres:5432/graderdb

# ── Redis ─────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── Docker sandbox ────────────────────────────────────────────
SANDBOX_IMAGE=c-sandbox:latest

# ── File uploads ──────────────────────────────────────────────
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE_MB=5

# ── AI Feedback (optional) ────────────────────────────────────
# Leave blank to use rule-based feedback only
ANTHROPIC_API_KEY=
USE_LLM_FEEDBACK=false
```

---

## Running the Platform

### Start everything

```bash
docker compose up -d
```

### Stop everything

```bash
docker compose down
```

### Full reset (delete all data)

```bash
docker compose down -v
docker rmi c-sandbox:latest
```

### View logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f postgres
```

### Sandbox health check

```bash
curl http://localhost:8000/health/sandbox
```

Expected response:
```json
{
  "healthy": true,
  "stdout": "SANDBOX_OK",
  "exit_code": 0
}
```

---

## Building the Sandbox Image

The sandbox image must be built **before** starting the platform. It contains GCC and runs all student code in complete isolation.

```bash
# From project root
cd backend/sandbox

# Linux / macOS
docker build --platform linux/amd64 --no-cache \
  -f Dockerfile.sandbox \
  -t c-sandbox:latest .

# Windows — fix line endings first
powershell -Command "(Get-Content runner.sh -Raw) -replace \"`r`n\",\"`n\" | Set-Content runner.sh -NoNewline -Encoding UTF8"
docker build --platform linux/amd64 --no-cache -f Dockerfile.sandbox -t c-sandbox:latest .
```

---

## Project Structure

```
c-tp-grader/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── assignment.py
│   │   │   ├── submission.py
│   │   │   └── notification.py
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── routers/         # FastAPI route handlers
│   │   │   ├── auth.py
│   │   │   ├── assignments.py
│   │   │   ├── submissions.py
│   │   │   ├── users.py
│   │   │   └── notifications.py
│   │   ├── services/        # Business logic
│   │   │   ├── execution_service.py
│   │   │   ├── evaluation_service.py
│   │   │   ├── test_generator.py
│   │   │   ├── static_analysis.py
│   │   │   ├── feedback_service.py
│   │   │   └── notification_service.py
│   │   ├── workers/         # Celery tasks
│   │   │   ├── celery_app.py
│   │   │   └── tasks.py
│   │   ├── utils/
│   │   │   ├── security.py
│   │   │   └── file_utils.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── sandbox/
│   │   ├── Dockerfile.sandbox
│   │   └── build_sandbox.py
│   ├── Dockerfile
│   ├── Dockerfile.worker
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── ScoreBadge.jsx
│   │   │   ├── StatusBadge.jsx
│   │   │   └── ProgressBar.jsx
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Assignments.jsx
│   │   │   ├── AssignmentDetail.jsx
│   │   │   ├── Submit.jsx
│   │   │   ├── Results.jsx
│   │   │   ├── Profile.jsx
│   │   │   ├── Students.jsx
│   │   │   └── StudentDetail.jsx
│   │   ├── store/
│   │   │   └── authStore.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── Dockerfile.frontend
│   ├── package.json
│   └── vite.config.js
├── uploads/                 # Uploaded files (created automatically)
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## User Roles

| Role | Capabilities |
|---|---|
| **Professor** | Create assignments, upload reference solutions, generate test cases, view all submissions, monitor student progress, override feedback |
| **Student** | View published assignments, submit C files, replace submissions before deadline, view evaluation results and feedback, receive notifications |

### Create your first professor account

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "prof1",
    "email": "prof@university.dz",
    "full_name": "Professor Ahmed",
    "password": "secret123",
    "role": "teacher"
  }'
```

### Create a student account

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student1",
    "email": "student@university.dz",
    "full_name": "Mohammed Saidi",
    "password": "secret123",
    "role": "student"
  }'
```

---

## API Documentation

The full interactive API documentation is available at:

```
http://localhost:8000/docs        ← Swagger UI
http://localhost:8000/redoc       ← ReDoc
```

### Main endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Login and receive JWT token |
| GET | `/api/v1/assignments` | List all assignments |
| POST | `/api/v1/assignments/create-with-files` | Create assignment with files |
| POST | `/api/v1/assignments/{id}/generate-tests` | Auto-generate test cases |
| POST | `/api/v1/submissions` | Submit or replace a solution |
| GET | `/api/v1/submissions/{id}/report` | Get full evaluation report |
| GET | `/api/v1/submissions/{id}/feedback` | Get structured feedback |
| GET | `/api/v1/users/students` | List all students (professor) |
| GET | `/api/v1/notifications` | Get user notifications |
| GET | `/health/sandbox` | Sandbox health check |

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "feat: add your feature description"`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Open a Pull Request

---

## License

This project is developed as a university thesis at university Abou Bakr Belkaid-Tlemcen, Department of Computer Science, Academic Year 2025–2026.

---

*Built with ❤️ for university C programming labs.*
