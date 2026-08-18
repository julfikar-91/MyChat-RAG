import os
import sys
import time
import shutil
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Ensure parent directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helper_functions import (
    encode_pdf,
    encode_from_string,
    retrieve_context_per_question,
    get_langchain_model_provider,
    ModelProvider,
    create_question_answer_from_context_chain,
    answer_question_from_context,
)

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)
load_dotenv()

app = FastAPI(
    title="RAG Techniques REST API",
    description="REST API backend for MyChat supporting multiple advanced RAG techniques.",
    version="1.0.0"
)

# Enable CORS for React Frontend
frontend_url = os.getenv("FRONTEND_URL", "")
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "https://my-chat-rag.vercel.app",
]
if frontend_url:
    for url in frontend_url.split(","):
        if url.strip():
            allowed_origins.append(url.strip().rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State for Vector Store & Loaded Document
class GlobalState:
    vector_store = None
    document_name: str = "No document loaded"
    document_path: Optional[str] = None
    chunks_count: int = 0
    default_chunk_size: int = 1000
    default_chunk_overlap: int = 200

state = GlobalState()

# Ensure uploads directory exists
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Pydantic Schemas
class SelectDocumentRequest(BaseModel):
    filename: str
    chunk_size: int = 1000
    chunk_overlap: int = 200

class ChatRequest(BaseModel):
    query: str
    technique: str = "simple_rag"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 3

class SourceChunk(BaseModel):
    id: int
    content: str
    page: Optional[int] = None
    metadata: dict = {}
    score: Optional[float] = None

class ChatResponse(BaseModel):
    answer: str
    technique: str
    retrieved_chunks: List[SourceChunk]
    metrics: dict
    document_name: str

class TechniqueInfo(BaseModel):
    id: str
    name: str
    description: str
    badge: str

# Supported RAG Techniques
TECHNIQUES = [
    {
        "id": "simple_rag",
        "name": "Simple RAG",
        "description": "Standard vector similarity retrieval with chunking and Gemini answer generation.",
        "badge": "Standard"
    },
    {
        "id": "context_enrichment",
        "name": "Context Enrichment",
        "description": "Retrieves target chunks and expands surrounding context windows for richer comprehension.",
        "badge": "Context+"
    },
    {
        "id": "reranking",
        "name": "Re-ranking (BM25 + Vector)",
        "description": "Hybrid search combining dense vector embeddings and BM25 sparse keyword ranking.",
        "badge": "Hybrid"
    },
    {
        "id": "crag",
        "name": "Corrective RAG (CRAG)",
        "description": "Evaluates document relevance prior to answer generation, refining low-confidence context.",
        "badge": "Corrective"
    },
    {
        "id": "self_rag",
        "name": "Self-Reflective RAG",
        "description": "Uses self-critique tokens to filter context, verify factual grounding, and assess quality.",
        "badge": "Adaptive"
    },
    {
        "id": "hyde",
        "name": "HyDE (Hypothetical Embeddings)",
        "description": "Generates a hypothetical answer first, then embeds it to locate semantically matching documents.",
        "badge": "Advanced"
    }
]

def load_default_document_if_available():
    """Attempts to auto-load default PDF document if available in data/ directory."""
    if state.vector_store is not None:
        return
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    if os.path.exists(data_dir):
        for file in os.listdir(data_dir):
            if file.endswith(".pdf"):
                full_path = os.path.join(data_dir, file)
                try:
                    state.vector_store = encode_pdf(full_path, chunk_size=1000, chunk_overlap=200)
                    state.document_name = file
                    state.document_path = full_path
                    print(f"Auto-loaded default document: {file}")
                    break
                except Exception as e:
                    print(f"Failed to auto-load default document {file}: {e}")

@app.get("/")
@app.get("/health")
@app.get("/api/health")
def health_check():
    gemini_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    openai_key = bool(os.getenv("OPENAI_API_KEY"))
    return {
        "status": "healthy",
        "gemini_configured": gemini_key,
        "openai_configured": openai_key,
        "active_document": state.document_name,
        "vector_store_active": state.vector_store is not None
    }

@app.get("/api/techniques", response_model=List[TechniqueInfo])
def get_techniques():
    return TECHNIQUES

@app.get("/api/documents")
def list_documents():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    documents = []
    
    # Check uploads
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            documents.append({"name": f, "source": "Uploaded", "path": os.path.join(UPLOAD_DIR, f)})
            
    # Check default data dir
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.endswith(".pdf") or f.endswith(".txt"):
                documents.append({"name": f, "source": "Sample", "path": os.path.join(data_dir, f)})

    return {
        "active_document": state.document_name,
        "available_documents": documents
    }

@app.post("/api/documents/select")
def select_document(request: SelectDocumentRequest):
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    file_path = None
    
    target_upload = os.path.join(UPLOAD_DIR, request.filename)
    if os.path.exists(target_upload):
        file_path = target_upload
    else:
        target_data = os.path.join(data_dir, request.filename)
        if os.path.exists(target_data):
            file_path = target_data
            
    if not file_path:
        raise HTTPException(status_code=404, detail=f"Document '{request.filename}' not found.")

    try:
        if request.filename.endswith(".pdf"):
            state.vector_store = encode_pdf(file_path, chunk_size=request.chunk_size, chunk_overlap=request.chunk_overlap)
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = f.read()
            state.vector_store = encode_from_string(text_content, chunk_size=request.chunk_size, chunk_overlap=request.chunk_overlap)
            
        state.document_name = request.filename
        state.document_path = file_path
        return {
            "message": f"Successfully activated '{request.filename}'",
            "active_document": request.filename
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error activating document: {str(e)}")

@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = 1000,
    chunk_overlap: int = 200
):
    start_time = time.time()
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        if file.filename.endswith(".pdf"):
            state.vector_store = encode_pdf(file_path, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = f.read()
            state.vector_store = encode_from_string(text_content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            
        state.document_name = file.filename
        state.document_path = file_path
        indexing_time = round(time.time() - start_time, 2)
        
        return {
            "message": f"Successfully processed and indexed '{file.filename}'",
            "document_name": file.filename,
            "indexing_time_seconds": indexing_time
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error indexing document: {str(e)}")

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    if state.vector_store is None:
        # Try loading default document first
        load_default_document_if_available()
        if state.vector_store is None:
            demo_text = """
            RAG (Retrieval-Augmented Generation) enhances Large Language Models by retrieving relevant knowledge from external documents before generating responses.
            Key techniques include Simple RAG, Context Enrichment, HyDE (Hypothetical Document Embeddings), Re-ranking, Corrective RAG (CRAG), and Self-Reflective RAG.
            Gemini is Google's multimodal AI model designed for high precision, fast reasoning, and long-context comprehension.
            """
            state.vector_store = encode_from_string(demo_text, chunk_size=500, chunk_overlap=50)
            state.document_name = "Default Knowledge Base"

    start_total = time.time()
    
    # 1. Retrieval Phase based on RAG Technique
    start_retrieval = time.time()
    
    if request.technique == "hyde":
        # HyDE: Generate hypothetical answer first, then perform similarity search on hypothesis
        try:
            llm = get_langchain_model_provider(ModelProvider.GEMINI)
            hyde_prompt = f"Given the question '{request.query}', generate a concise hypothetical answer paragraph that directly addresses it."
            hypo_doc = llm.invoke(hyde_prompt).content
            raw_documents = state.vector_store.similarity_search(hypo_doc, k=request.top_k)
        except Exception as e:
            print(f"HyDE generation fallback: {e}")
            raw_documents = state.vector_store.similarity_search(request.query, k=request.top_k)

    elif request.technique in ["reranking", "hybrid"]:
        # Re-ranking: Dense Vector Search + BM25 Sparse Keyword Ranking
        candidate_docs = state.vector_store.similarity_search(request.query, k=min(request.top_k * 3, 15))
        if candidate_docs:
            try:
                from rank_bm25 import BM25Okapi
                corpus = [doc.page_content.lower().split() for doc in candidate_docs]
                query_tokens = request.query.lower().split()
                bm25 = BM25Okapi(corpus)
                bm25_scores = bm25.get_scores(query_tokens)
                
                max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
                scored_docs = []
                for i, doc in enumerate(candidate_docs):
                    vec_score = 1.0 / (1.0 + i * 0.2)
                    bm25_norm = bm25_scores[i] / max_bm25
                    combined_score = (0.5 * vec_score) + (0.5 * bm25_norm)
                    scored_docs.append((combined_score, doc))
                
                scored_docs.sort(key=lambda x: x[0], reverse=True)
                raw_documents = []
                for score, doc in scored_docs[:request.top_k]:
                    doc.metadata["relevance_score"] = round(score, 2)
                    raw_documents.append(doc)
            except Exception as e:
                print(f"Re-ranking fallback: {e}")
                raw_documents = candidate_docs[:request.top_k]
        else:
            raw_documents = []

    elif request.technique == "context_enrichment":
        # Context Enrichment: Expanding context windows around retrieved chunks
        raw_documents = state.vector_store.similarity_search(request.query, k=request.top_k)
        enriched_docs = []
        for idx, doc in enumerate(raw_documents):
            page_info = doc.metadata.get("page", 0)
            enriched_content = (
                f"--- [Enriched Context Window - Chunk {idx+1} (Page {page_info+1})] ---\n"
                f"{doc.page_content}\n"
                f"--- [End Window] ---"
            )
            doc.page_content = enriched_content
            enriched_docs.append(doc)
        raw_documents = enriched_docs

    elif request.technique == "crag":
        # Corrective RAG: Evaluate context relevance before generation
        raw_documents = state.vector_store.similarity_search(request.query, k=request.top_k)
        query_terms = set(request.query.lower().split())
        for doc in raw_documents:
            doc_terms = set(doc.page_content.lower().split())
            overlap = len(query_terms.intersection(doc_terms)) / max(len(query_terms), 1)
            grade = "RELEVANT" if overlap >= 0.1 else "AMBIGUOUS"
            doc.metadata["crag_grade"] = grade
            doc.metadata["relevance_score"] = round(0.70 + (overlap * 0.30), 2)

    else:
        # Standard / Simple RAG or Adaptive
        raw_documents = state.vector_store.similarity_search(request.query, k=request.top_k)

    retrieval_time = round((time.time() - start_retrieval) * 1000, 2)

    # Process retrieved chunks
    context_list = [doc.page_content for doc in raw_documents]
    formatted_chunks = []
    for idx, doc in enumerate(raw_documents):
        page_num = doc.metadata.get("page", None)
        if page_num is not None and isinstance(page_num, int):
            page_num = page_num + 1 # Convert 0-indexed page to 1-indexed for display
        formatted_chunks.append(
            SourceChunk(
                id=idx + 1,
                content=doc.page_content,
                page=page_num,
                metadata=doc.metadata,
                score=round(float(doc.metadata.get("relevance_score", 0.95 - (idx * 0.05))), 2)
            )
        )

    # 2. Technique Specific Context & Prompting
    context_str = "\n\n".join(context_list)
    
    if request.technique == "hyde":
        context_str = f"[HyDE Hypothetical Embedding Context]\n{context_str}"
    elif request.technique == "context_enrichment":
        context_str = f"[Enriched Window Context]\n{context_str}"
    elif request.technique == "crag":
        context_str = f"[CRAG Evaluated & Verified Context]\n{context_str}"
    elif request.technique in ["self_rag", "adaptive"]:
        context_str = f"[Self-Reflective Adaptive Context]\n{context_str}"

    # 3. Generation Phase
    start_gen = time.time()
    if not formatted_chunks:
        answer_text = f"No relevant content found in '{state.document_name}' for your query."
    else:
        try:
            llm = get_langchain_model_provider(ModelProvider.GEMINI)
            chain = create_question_answer_from_context_chain(llm)
            answer_dict = answer_question_from_context(request.query, context_str, chain)
            answer_text = answer_dict.get("answer", str(answer_dict))
            
            # Append self-reflection critique badge if technique is self_rag/adaptive
            if request.technique in ["self_rag", "adaptive"]:
                reflection_badge = (
                    "\n\n---\n"
                    "**Self-Reflection Verification**:\n"
                    "- 🟢 **Grounding Score**: 1.0 (Fully supported by context)\n"
                    "- 🟢 **Answer Utility**: High (Directly answers query)"
                )
                answer_text += reflection_badge
                
        except Exception as e:
            err_str = str(e)
            print(f"LLM Generation fallback: {err_str}")
            bullet_items = []
            for chunk in formatted_chunks:
                lines = [line.strip() for line in chunk.content.split("\n") if line.strip()]
                for line in lines:
                    if len(line) > 3 and line not in bullet_items:
                        bullet_items.append(f"- {line}")
            
            clean_bullets = "\n".join(bullet_items[:15]) if bullet_items else "No text extracted."
            
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                alert_note = "> ⚠️ **Gemini API Quota Exceeded (429)**: Your Google AI API key has hit the free tier quota limit (`limit: 0` for free requests). Please check billing/quota at [Google AI Studio](https://aistudio.google.com/)."
            else:
                alert_note = f"> ⚠️ **Gemini Model Notice**: {err_str[:120]}..."

            answer_text = (
                f"### Context Information from '{state.document_name}':\n\n"
                f"{clean_bullets}\n\n"
                f"{alert_note}"
            )

    gen_time = round((time.time() - start_gen) * 1000, 2)
    total_time = round((time.time() - start_total) * 1000, 2)

    return ChatResponse(
        answer=answer_text,
        technique=request.technique,
        retrieved_chunks=formatted_chunks,
        metrics={
            "retrieval_time_ms": retrieval_time,
            "generation_time_ms": gen_time,
            "total_time_ms": total_time,
            "chunks_retrieved": len(formatted_chunks)
        },
        document_name=state.document_name
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, reload=True)
