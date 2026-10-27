"""Public RAG frontend routes.

GET  /rag      -> chat page where any visitor can ask clinic questions
POST /rag/api  -> JSON endpoint used by the page: {"question": "..."}
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

MAX_QUESTION_CHARS = 500

_pipeline = None


def get_pipeline():
    """Create the RAG pipeline on first use so the app still starts
    even if the index has not been built yet."""
    global _pipeline
    if _pipeline is None:
        from rag.rag_pipeline import RAGPipeline
        _pipeline = RAGPipeline()
    return _pipeline


@router.get("/rag", response_class=HTMLResponse)
async def rag_page(request: Request):
    logger.info("RAG chat page accessed")
    return templates.TemplateResponse(request, "rag_chat.html")


@router.post("/rag/api")
async def rag_api(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid request."}, status_code=400)

    question = str(body.get("question", "")).strip()
    if not question:
        return JSONResponse({"error": "Please enter a question."}, status_code=400)
    if len(question) > MAX_QUESTION_CHARS:
        return JSONResponse(
            {"error": f"Question is too long (max {MAX_QUESTION_CHARS} characters)."},
            status_code=400,
        )

    try:
        result = get_pipeline().answer(question)
    except Exception:
        logger.exception("RAG request failed")
        return JSONResponse(
            {"error": "Sorry, the assistant is unavailable right now. Please try again later."},
            status_code=500,
        )

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "chunks": [
            {
                "source": c["source"],
                "score": c["score"],
                "text": c["text"],
            }
            for c in result["retrieved_chunks"]
        ],
    }
