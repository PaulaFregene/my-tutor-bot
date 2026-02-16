import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

# --- CORS CONFIGURATION (CRITICAL FIX) ---
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

# MOUNT PDF DIRECTORY
Path(PDF_UPLOAD_DIR).mkdir(exist_ok=True)
app.mount("/pdfs", StaticFiles(directory=PDF_UPLOAD_DIR), name="pdfs")

# Display names storage
DISPLAY_NAMES_FILE = Path("display_names.json")


def load_display_names():
    if DISPLAY_NAMES_FILE.exists():
        try:
            with open(DISPLAY_NAMES_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Could not load display names: {e}")
    return {}


def save_display_names(display_names: dict):
    try:
        with open(DISPLAY_NAMES_FILE, "w") as f:
            json.dump(display_names, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Could not save display names: {e}")


@app.get("/")
async def root():
    return {"message": "MyTutorBot Backend is Running"}


# --- HEALTH CHECK (CRITICAL FIX) ---
@app.get("/health")
async def health_check():
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "s3_enabled": is_s3_enabled(),
    }
    return health_data


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename:
        return {"status": "error", "message": "No filename provided"}
    if not file.filename.endswith(".pdf"):
        return {"status": "error", "message": "Only PDF files allowed"}

    file_path = Path(PDF_UPLOAD_DIR) / file.filename
    file_content = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_content)

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
    modified_question = apply_its_mode(req.question, req.mode)
    citations = []
    answer = "Error processing request."

    try:
        result = query_rag(modified_question, SYSTEM_PROMPT)
        answer = result["answer"]
        citations = result["citations"]
    except Exception as e:
        print(f"Error: {e}")
        answer = "I'm having trouble accessing the course materials right now."

    save_message(req.anon_user_id, "user", req.question, req.mode)
    save_message(req.anon_user_id, "assistant", answer, req.mode)

    return {"content": answer, "citations": citations, "role": "assistant"}


@app.post("/api/history")
async def get_conversation_history(req: HistoryRequest):
    return {"conversation": get_history(req.anon_user_id)}


@app.get("/api/files")
async def list_files():
    if is_s3_enabled():
        files = list_s3_pdfs()
    else:
        files = [f.name for f in Path(PDF_UPLOAD_DIR).glob("*.pdf")]

    display_names = load_display_names()
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
    try:
        data = await request.json()
        filename = data.get("filename")
        if not filename:
            return {"status": "error", "message": "Filename required"}

        file_path = Path(PDF_UPLOAD_DIR) / filename
        delete_pdf_from_database(filename)

        if is_s3_enabled():
            delete_file_from_s3(filename)

        if file_path.exists():
            file_path.unlink()

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
    try:
        data = await request.json()
        filename = data.get("filename")
        display_name = data.get("display_name", "").strip()

        if not filename:
            return {"status": "error", "message": "Filename required"}

        file_path = Path(PDF_UPLOAD_DIR) / filename
        if not file_path.exists():
            return {"status": "error", "message": "File not found"}

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
