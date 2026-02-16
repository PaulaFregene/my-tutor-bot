# MyTutorBot 🎓🧠🤖
AI-powered tutoring assistant with Intelligent Tutoring System (ITS) modes for personalized learning.

CS Researcher: Paula Eyituoyo Fregene (Northwestern University)
CS Research Mentor: Professor Yiji Zhang (Northwestern Univerity)
Research Experiement Group: Winter '26 CS 211: Foundamental of Computer Science 2 (teaches C and C++) @ Northwestern University

## Features
- 📚 PDF-based RAG (Retrieval Augmented Generation)
- 🤖 Multiple tutoring modes (Direct, Guided Socratic)
- 💬 Conversation history per student
- 📊 Citation tracking with page numbers
- 👨‍💼 Admin panel for content management
- ☁️ S3 integration for scalable PDF storage

## Quick Start

### Local Development
```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload --reload-dir .

# Frontend
cd frontend
npm install
npm run dev
```

### Upload PDFs
```powershell
# After uploading PDFs, reindex them:
Invoke-WebRequest -Uri http://localhost:8000/api/ingest -Method POST
```

## Documentation

- 📖 **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deploy to Railway with S3
- 📊 **[SCALING_PLAN.md](SCALING_PLAN.md)** - Scale to 100+ concurrent users
- ⚡ **[PERFORMANCE_FAQ.md](PERFORMANCE_FAQ.md)** - Quick performance guide
- 🧪 **Load Testing:** `locust -f backend/load_test.py`

## Architecture

```
Frontend (Next.js) → Backend (FastAPI) → Groq LLM
                            ↓
                    Local ChromaDB (vectors)
                    SQLite (chat history)
                    S3 (PDF storage)
```

**Perfect for 100 concurrent users!** No Chroma Cloud needed. See [PERFORMANCE_FAQ.md](PERFORMANCE_FAQ.md) for details.

## Tech Stack
- **Frontend:** Next.js 15, TypeScript, TailwindCSS
- **Backend:** FastAPI, Python 3.10+
- **RAG:** LlamaIndex + ChromaDB (local)
- **LLM:** Groq (Llama 3.3 70B)
- **Storage:** S3, SQLite
- **Auth:** Clerk 

## Development