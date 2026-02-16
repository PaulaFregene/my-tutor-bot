"""
Local RAG Engine using LlamaIndex + Chroma
Replaces LlamaCloud with local, controlled RAG stack
"""

import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq
from llama_index.vector_stores.chroma import ChromaVectorStore

from s3_storage import (
    download_file_from_s3,
    ensure_pdf_local,
    is_s3_enabled,
    list_s3_pdfs,
)

try:
    import pypdf

    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
    print(
        "[WARNING] pypdf not installed. Install it for better page number accuracy: pip install pypdf"
    )

load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHROMA_PATH = "./chroma_db"
PDF_UPLOAD_DIR = "./uploaded_pdfs"

Path(CHROMA_PATH).mkdir(exist_ok=True)
Path(PDF_UPLOAD_DIR).mkdir(exist_ok=True)

# Settings
Settings.llm = Groq(
    model="llama-3.3-70b-versatile", temperature=0.7, api_key=GROQ_API_KEY
)
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

# Init Chroma
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
chroma_collection = chroma_client.get_or_create_collection("course_materials")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

index = None


def get_accurate_page_number(file_path: str, content_snippet: str) -> str:
    """
    Get accurate page number from PDF file.
    Uses pypdf if available, otherwise falls back to page_label.
    Downloads from S3 if necessary.
    """
    if not HAS_PYPDF:
        return "?"

    try:
        pdf_path = Path(file_path)

        # If file doesn't exist locally and S3 is enabled, try to get it from S3
        if not pdf_path.exists() and is_s3_enabled():
            filename = pdf_path.name
            pdf_path = ensure_pdf_local(filename, Path(PDF_UPLOAD_DIR))
            if pdf_path is None:
                print(f"[DEBUG] PDF file not found locally or in S3: {file_path}")
                return "?"

        # Check if file exists
        if not pdf_path.exists():
            print(f"[DEBUG] PDF file not found: {file_path}")
            return "?"

        with open(pdf_path, "rb") as pdf_file:
            reader = pypdf.PdfReader(pdf_file)
            total_pages = len(reader.pages)

            if not content_snippet or len(content_snippet) < 10:
                # Not enough content to search for
                return "?"

            # Get first 50 characters of content to search for
            search_text = content_snippet[:50].strip()

            # Search for the snippet in each page
            for page_num in range(total_pages):
                try:
                    page = reader.pages[page_num]
                    text = page.extract_text()

                    # Use a more flexible matching - check if any substring matches
                    if search_text in text or text.find(search_text[:30]) >= 0:
                        return str(page_num + 1)  # +1 because pages are 0-indexed
                except Exception as page_e:
                    print(f"[DEBUG] Error reading page {page_num}: {page_e}")
                    continue
    except Exception as e:
        print(f"[DEBUG] Could not extract accurate page number from {file_path}: {e}")

    return "?"


def initialize_index():
    global index
    try:
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
        )
        print("[RAG] Loaded existing index")
    except Exception:
        index = VectorStoreIndex.from_documents([], storage_context=storage_context)
        print("[RAG] Created new empty index")


def ingest_pdfs(pdf_directory: str = PDF_UPLOAD_DIR):
    global index
    print(f"[INGEST] Loading PDFs from {pdf_directory}")

    # If S3 is enabled, sync PDFs from S3 to local directory first
    if is_s3_enabled():
        print("[INGEST] S3 enabled, syncing PDFs from S3...")
        s3_files = list_s3_pdfs()
        pdf_dir = Path(pdf_directory)

        for filename in s3_files:
            local_path = pdf_dir / filename
            if not local_path.exists():
                print(f"[INGEST] Downloading {filename} from S3...")
                s3_key = f"pdfs/{filename}"
                download_file_from_s3(s3_key, local_path)

    try:
        documents = SimpleDirectoryReader(pdf_directory).load_data()
        if not documents:
            return {"status": "error", "message": "No PDFs found"}

        index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context, show_progress=True
        )
        return {"status": "success", "document_count": len(documents)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def query_rag(
    question: str, system_prompt: str, chat_history: list = []
):  # <--- Added argument
    global index
    if index is None:
        initialize_index()

    # Format history
    history_str = ""
    if chat_history:
        # DB already limits to 10, so we just join them
        history_str = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history]
        )

    try:
        # Create engine
        query_engine = index.as_query_engine(
            similarity_top_k=10,
            response_mode="compact",
        )

        # Prompt construction (Fixed to include history)
        full_query = f"""
{system_prompt}

PREVIOUS CONVERSATION HISTORY:
{history_str}

INSTRUCTION:
Based on the course materials provided and the conversation history above, answer this question:
{question}
"""

        response = query_engine.query(full_query)
        answer_text = str(response)

        if "I cannot find this information" in answer_text:
            citations = []
        else:
            # Extract Citations with accurate page numbers
            citations = []
            seen = set()
            if hasattr(response, "source_nodes"):
                for node in response.source_nodes:
                    metadata = node.node.metadata
                    file_name = metadata.get("file_name", "Unknown File")

                    # Try to get accurate page number
                    page_label = metadata.get("page_label", "?")

                    # If we have page label, try to get accurate page from PDF
                    if HAS_PYPDF and file_name and file_name != "Unknown File":
                        pdf_path = Path(PDF_UPLOAD_DIR) / file_name
                        if pdf_path.exists():
                            # Get snippet of content to search for
                            content_snippet = (
                                node.get_content()
                                if hasattr(node, "get_content")
                                else ""
                            )
                            if not content_snippet:
                                # Try alternative ways to get content
                                if hasattr(node, "text"):
                                    content_snippet = node.text
                                elif hasattr(node, "content"):
                                    content_snippet = node.content
                                else:
                                    content_snippet = str(node)

                            accurate_page = get_accurate_page_number(
                                str(pdf_path), content_snippet
                            )
                            page_label = (
                                accurate_page if accurate_page != "?" else page_label
                            )

                    citation_key = f"{file_name}|{page_label}"
                    if citation_key not in seen:
                        seen.add(citation_key)
                        citations.append(f"{file_name} (Page {page_label})")

        return {"answer": answer_text, "citations": citations}

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise e


def delete_pdf_from_database(pdf_filename: str):
    """
    Delete all embeddings of a specific PDF from the Chroma database.
    This ensures deleted PDFs don't appear in query results.
    """
    try:
        collection = chroma_client.get_collection("course_materials")

        # Query for all documents with this file name
        # Get all metadata to find entries for this file
        results = collection.get(where={"file_name": pdf_filename})

        if results and results["ids"]:
            # Delete all found documents
            collection.delete(ids=results["ids"])
            print(
                f"[DELETE] Removed {len(results['ids'])} embeddings for {pdf_filename}"
            )
            return True
        else:
            print(f"[DELETE] No embeddings found for {pdf_filename}")
            return True
    except Exception as e:
        print(f"[DELETE ERROR] Could not delete {pdf_filename} from database: {e}")
        return False


def get_index_stats():
    try:
        collection = chroma_client.get_collection("course_materials")
        return {"status": "success", "document_count": collection.count()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


initialize_index()
