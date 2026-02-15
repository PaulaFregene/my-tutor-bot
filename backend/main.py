# FastAPI entrypoint
import time
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from prompts import SYSTEM_PROMPT
from its import apply_its_mode
from rag_engine import query_rag, ingest_pdfs, get_index_stats, PDF_UPLOAD_DIR
from db import save_message, get_history
from models import QueryRequest, HistoryRequest

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "MyTutorBot Backend API - Local RAG",
        "endpoints": [
            "/api/query",
            "/api/history",
            "/api/upload",
            "/api/ingest",
            "/api/stats",
        ],
    }


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file for indexing"""
    if not file.filename.endswith(".pdf"):
        return {"status": "error", "message": "Only PDF files are allowed"}

    try:
        # Save the PDF
        file_path = Path(PDF_UPLOAD_DIR) / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        print(f"[UPLOAD] Saved {file.filename} ({len(content)} bytes)")
        return {
            "status": "success",
            "message": f"Uploaded {file.filename}",
            "filename": file.filename,
        }
    except Exception as e:
        print(f"[UPLOAD ERROR] {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/ingest")
async def ingest():
    """Ingest all PDFs in the upload directory"""
    result = ingest_pdfs()
    return result


@app.get("/api/stats")
async def stats():
    """Get index statistics"""
    return get_index_stats()


@app.post("/api/query")
async def query_ai(req: QueryRequest):
    # ITS behavior
    question = apply_its_mode(req.question, req.mode)

    answer = "Sorry, I encountered an error while processing your question. Please try again."
    try:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Query attempt {attempt + 1}/{max_retries}")
                answer = query_rag(question, SYSTEM_PROMPT)
                print(f"Got answer: {answer[:100]}...")
                break
            except Exception as e:
                print(
                    f"Error querying RAG (attempt {attempt + 1}): {type(e).__name__}: {e}"
                )
                import traceback

                traceback.print_exc()
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
                else:
                    answer = "Sorry, I encountered an error while processing your question. Please try again."
    except Exception as e:
        # This shouldn't happen, but just in case
        print(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        answer = "Sorry, I encountered an error while processing your question. Please try again."

    # Research logging
    try:
        save_message(req.anon_user_id, "user", req.question, req.mode)
        save_message(req.anon_user_id, "assistant", answer, req.mode)
    except Exception as e:
        print(f"Error saving message: {e}")

    return {"content": answer}


@app.post("/api/history")
async def get_conversation_history(req: HistoryRequest):
    try:
        history = get_history(req.anon_user_id)
        return {"conversation": history}
    except Exception as e:
        print(f"Error getting history: {e}")
        return {"conversation": []}
