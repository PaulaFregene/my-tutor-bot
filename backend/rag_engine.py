"""
Local RAG Engine using LlamaIndex + Chroma
Replaces LlamaCloud with local, controlled RAG stack
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import chromadb

load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHROMA_PATH = "./chroma_db"
PDF_UPLOAD_DIR = "./uploaded_pdfs"

# Create directories if they don't exist
Path(CHROMA_PATH).mkdir(exist_ok=True)
Path(PDF_UPLOAD_DIR).mkdir(exist_ok=True)

# Configure LlamaIndex settings
Settings.llm = Groq(
    model="llama-3.3-70b-versatile", temperature=0.7, api_key=GROQ_API_KEY
)
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

# Initialize Chroma client
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
chroma_collection = chroma_client.get_or_create_collection("course_materials")

# Create vector store
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Global index (loaded on startup if exists)
index = None


def initialize_index():
    """Initialize or load existing index"""
    global index
    try:
        # Try to load existing index
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
        )
        print("[RAG] Loaded existing index from Chroma")
    except Exception as e:
        print(f"[RAG] No existing index found: {e}")
        # Create empty index
        index = VectorStoreIndex.from_documents(
            [],
            storage_context=storage_context,
        )
        print("[RAG] Created new empty index")


def ingest_pdfs(pdf_directory: str = PDF_UPLOAD_DIR):
    """
    Ingest all PDFs from a directory into the vector store
    """
    global index

    print(f"[INGEST] Loading PDFs from {pdf_directory}")

    try:
        # Load documents
        documents = SimpleDirectoryReader(pdf_directory).load_data()
        print(f"[INGEST] Loaded {len(documents)} documents")

        if not documents:
            return {"status": "error", "message": "No PDFs found"}

        # Create/update index
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            show_progress=True,
        )

        print(f"[INGEST] Successfully indexed {len(documents)} documents")
        return {
            "status": "success",
            "message": f"Indexed {len(documents)} documents",
            "document_count": len(documents),
        }

    except Exception as e:
        print(f"[INGEST ERROR] {e}")
        return {"status": "error", "message": str(e)}


def query_rag(question: str, system_prompt: str) -> str:
    """
    Query the RAG system with a question

    Flow:
    1. Retrieve relevant chunks from vector store
    2. Generate answer using LLM with system prompt
    """
    global index

    if index is None:
        initialize_index()

    print(f"[QUERY] Question: {question[:100]}...")

    try:
        # Create query engine with custom prompt
        query_engine = index.as_query_engine(
            similarity_top_k=3,  # Top 3 chunks
            response_mode="compact",
        )

        # Build full prompt with system instructions
        full_query = f"""
{system_prompt}

Based on the course materials provided, answer this question:
{question}
"""

        print("[QUERY] Retrieving relevant chunks...")
        response = query_engine.query(full_query)

        answer = str(response)
        print(f"[QUERY] Generated answer ({len(answer)} chars)")

        # Get source information
        source_nodes = (
            response.source_nodes if hasattr(response, "source_nodes") else []
        )
        print(f"[QUERY] Used {len(source_nodes)} source chunks")

        return answer

    except Exception as e:
        print(f"[QUERY ERROR] {e}")
        import traceback

        traceback.print_exc()
        raise


def get_index_stats():
    """Get statistics about the current index"""
    try:
        collection = chroma_client.get_collection("course_materials")
        count = collection.count()
        return {
            "status": "success",
            "document_count": count,
            "index_initialized": index is not None,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Initialize on module load
initialize_index()
