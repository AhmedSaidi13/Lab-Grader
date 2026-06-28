@echo off
IF "%1"=="up" (
    echo Building sandbox image...
    cd backend\sandbox
    docker build --platform linux/amd64 --no-cache -f Dockerfile.sandbox -t c-sandbox:latest .
    cd ..\..
    echo Starting services...
    docker compose up --build -d
    echo Done. API: http://localhost:8000  Frontend: http://localhost:5173
)
IF "%1"=="down" (
    docker compose down
)
IF "%1"=="reset" (
    docker compose down -v
    docker rmi c-sandbox:latest 2>nul
    cd backend\sandbox
    docker build --platform linux/amd64 --no-cache -f Dockerfile.sandbox -t c-sandbox:latest .
    cd ..\..
    docker compose up --build -d
)
IF "%1"=="logs" (
    docker compose logs -f %2
)