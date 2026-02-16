import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # Import this

from db import get_history, save_message
from its import apply_its_mode
from models import HistoryRequest, QueryRequest
from prompts import SYSTEM_PROMPT
from rag_engine import (
    PDF_UPLOAD_DIR,
    delete_pdf_from_database,
    get_index_stats,
    ingest_pdfs,
    query_rag,
)
from s3_storage import (
    delete_file_from_s3,
    get_s3_file_url,
    is_s3_enabled,
    list_s3_pdfs,
    upload_file_to_s3,
)

load_dotenv()

app = FastAPI()

# CORS configuration - allow both local dev and production
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3000/",
]

# Add production frontend URL from environment
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MOUNT PDF DIRECTORY AS STATIC FILES
# This allows http://localhost:8000/pdfs/lecture1.pdf to work
Path(PDF_UPLOAD_DIR).mkdir(exist_ok=True)
app.mount("/pdfs", StaticFiles(directory=PDF_UPLOAD_DIR), name="pdfs")

# Display names storage
DISPLAY_NAMES_FILE = Path("display_names.json")


def load_display_names():
    """Load display name mappings from JSON file"""
    if DISPLAY_NAMES_FILE.exists():
        try:
            with open(DISPLAY_NAMES_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Could not load display names: {e}")
    return {}


def save_display_names(display_names: dict):
    """Save display name mappings to JSON file"""
    try:
        with open(DISPLAY_NAMES_FILE, "w") as f:
            json.dump(display_names, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Could not save display names: {e}")


@app.get("/")
async def root():
    return {"message": "MyTutorBot Backend is Running"}


@app.get("/health")
async def health_check():
    """Health check endpoint with performance metrics"""
    import time

    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "s3_enabled": is_s3_enabled(),
    }

    # Test ChromaDB
    try:
        stats = get_index_stats()
        health_data["chromadb"] = {
            "status": "ok",
            "documents": stats.get("document_count", 0),
        }
    except Exception as e:
        health_data["chromadb"] = {"status": "error", "message": str(e)}

    # Test database
    try:
        history = get_history("health_check", limit=1)
        health_data["database"] = {"status": "ok", "type": "sqlite"}
    except Exception as e:
        health_data["database"] = {"status": "error", "message": str(e)}

    # S3 status
    if is_s3_enabled():
        try:
            pdf_count = len(list_s3_pdfs())
            health_data["s3"] = {"status": "ok", "pdf_count": pdf_count}
        except Exception as e:
            health_data["s3"] = {"status": "error", "message": str(e)}

    return health_data


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        return {"status": "error", "message": "Only PDF files allowed"}

    # Save locally first (needed for RAG ingestion)
    file_path = Path(PDF_UPLOAD_DIR) / file.filename
    file_content = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_content)

    # Upload to S3 if enabled
    if is_s3_enabled():
        success = upload_file_to_s3(file_path)
        if not success:
            return {
                "status": "warning",
                "message": "File saved locally but S3 upload failed",
                "filename": file.filename,
            }

    return {"status": "success", "filename": file.filename}


@app.post("/api/ingest")
async def ingest():
    return ingest_pdfs()


@app.post("/api/query")
async def query_ai(req: QueryRequest):
    # ITS Logic: Modify the question based on mode
    modified_question = apply_its_mode(req.question, req.mode)

    citations = []
    answer = "Error processing request."

    try:
        # Call RAG
        result = query_rag(modified_question, SYSTEM_PROMPT)
        answer = result["answer"]
        citations = result["citations"]
    except Exception as e:
        print(f"Error: {e}")
        answer = "I'm having trouble accessing the course materials right now."

    # Save to DB
    save_message(req.anon_user_id, "user", req.question, req.mode)
    save_message(req.anon_user_id, "assistant", answer, req.mode)

    return {"content": answer, "citations": citations, "role": "assistant"}


@app.post("/api/history")
async def get_conversation_history(req: HistoryRequest):
    return {"conversation": get_history(req.anon_user_id)}


@app.get("/api/files")
async def list_files():
    """List available PDFs for the frontend sidebar with their display names"""
    # Get files from S3 if enabled, otherwise from local directory
    if is_s3_enabled():
        files = list_s3_pdfs()
    else:
        files = [f.name for f in Path(PDF_UPLOAD_DIR).glob("*.pdf")]

    display_names = load_display_names()

    # Generate presigned URLs for S3 files if needed
    file_urls = {}
    if is_s3_enabled():
        for filename in files:
            url = get_s3_file_url(filename)
            if url:
                file_urls[filename] = url

    return {
        "files": files,
        "display_names": display_names,
        "file_urls": file_urls if file_urls else None,
    }


@app.post("/api/delete-pdf")
async def delete_pdf(request: Request):
    """Delete a PDF file and remove it from the Chroma database"""
    try:
        data = await request.json()
        filename = data.get("filename")
        if not filename:
            return {"status": "error", "message": "Filename required"}

        file_path = Path(PDF_UPLOAD_DIR) / filename

        # Step 1: Delete from Chroma database first
        delete_pdf_from_database(filename)

        # Step 2: Delete from S3 if enabled
        if is_s3_enabled():
            delete_file_from_s3(filename)

        # Step 3: Delete local file if it exists
        if file_path.exists():
            file_path.unlink()
            print(f"[DELETE] Deleted local file: {filename}")

        # Step 4: Remove from display names if it exists
        display_names = load_display_names()
        if filename in display_names:
            del display_names[filename]
            save_display_names(display_names)

        return {"status": "success", "message": f"Deleted {filename}"}
    except Exception as e:
        print(f"[DELETE ERROR] {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/set-display-name")
async def set_display_name(request: Request):
    """Set the display name for a PDF file"""
    try:
        data = await request.json()
        filename = data.get("filename")
        display_name = data.get("display_name", "").strip()

        if not filename:
            return {"status": "error", "message": "Filename required"}

        # Validate file exists
        file_path = Path(PDF_UPLOAD_DIR) / filename
        if not file_path.exists():
            return {"status": "error", "message": "File not found"}

        # Load, update, and save display names
        display_names = load_display_names()

        if display_name:
            display_names[filename] = display_name
        elif filename in display_names:
            del display_names[filename]

        save_display_names(display_names)

        return {
            "status": "success",
            "message": f"Display name updated",
            "display_name": display_names.get(filename, filename),
        }
    except Exception as e:
        print(f"[SET-DISPLAY-NAME ERROR] {e}")
        return {"status": "error", "message": str(e)}
