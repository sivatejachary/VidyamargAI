# HireAI - Recruiter Operating System

HireAI is an enterprise AI recruitment platform powered by **Tara AI**.

## How to Setup and Run Local Servers

To start the platform, you must run both the **FastAPI backend** (Port 8000) and the **Next.js frontend** (Port 3000).

### Method A: Single Command Run (Recommended)

From the root directory of this project (`c:\Users\jshiv\Downloads\shivateja`), run the following commands in your shell:

1. **Install all packages (python and npm)**:
   ```bash
   npm run install:all
   ```
2. **Start both servers concurrently**:
   ```bash
   npm run dev
   ```

---

### Method B: Manual Run (In Separate Terminals)

If you prefer to start each service in its own window:

#### 1. Start backend (From the project root directory):
```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API documentation will be active at: `http://localhost:8000/docs`.

#### 2. Start frontend:
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```
The web portal will be active at: `http://localhost:3000`.

---

## Method C: Docker Compose

If you have Docker running locally, you can deploy the complete stack (including Postgres, Redis, and MinIO storage) in a single command:
```bash
docker-compose up --build
```
- **Web App**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **MinIO Console**: `http://localhost:9001`
