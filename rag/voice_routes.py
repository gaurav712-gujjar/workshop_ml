import re
from urllib.parse import urlparse

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from rag.routes import get_pipeline
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

MAX_QUESTION_CHARS = 500
RAG_MIN_SCORE = 0.12  # best chunk must score at least this to trust the knowledge base
WEB_RESULTS = 5

# Web answers are limited to these trusted health sites
TRUSTED_DOMAINS = ["who.int", "cdc.gov", "nhs.uk", "mohfw.gov.in", "icmr.gov.in"]

NO_ANSWER = (
    "Sorry, I could not find reliable information on that. "
    "Please consult a doctor or the clinic reception."
)


def clean_for_speech(text: str) -> str:
    """Strip markdown so the spoken reply sounds natural."""
    text = re.sub(r"[*_#`>|]", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def is_trusted(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in TRUSTED_DOMAINS)


def web_search(question: str) -> list:
    """DuckDuckGo search (no API key), keeping only trusted health sites."""
    from ddgs import DDGS

    site_filter = " OR ".join(f"site:{d}" for d in TRUSTED_DOMAINS)
    try:
        raw = DDGS().text(f"{question} ({site_filter})", max_results=WEB_RESULTS)
    except Exception:
        logger.exception("Web search failed")
        return []

    results = []
    for r in raw or []:
        url = r.get("href", "")
        if url.startswith(("http://", "https://")) and is_trusted(url):
            results.append({
                "title": r.get("title", url),
                "url": url,
                "snippet": r.get("body", ""),
            })
    return results


def answer_from_web(pipeline, question: str, results: list) -> str:
    generator = pipeline.generator
    if generator.client is None:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    context = "\n\n".join(
        f"[{r['title']}] ({r['url']})\n{r['snippet']}" for r in results
    )
    prompt = f"""Web search results from trusted health sites:

{context}

Patient's question:
{question}

Instructions:
- Answer using only the search results above.
- Reply in the same language as the question (English or Hinglish).
- This answer will be spoken aloud: use plain sentences, no markdown, no lists.
- Keep it to 2-4 short sentences.
- Do not prescribe medicines or dosages.
- Say this is general information, not a diagnosis, and suggest a doctor if unsure.
- If the results do not answer the question, say so."""

    response = generator.client.chat.completions.create(
        model=generator.config["model"],
        max_tokens=generator.config["max_tokens"],
        messages=[
            {"role": "system", "content": generator.config["system_prompt"]},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def handle_question(question: str) -> dict:
    pipeline = get_pipeline()

    # 1) Clinic knowledge base first
    chunks = pipeline.retriever.retrieve(question)
    if chunks and max(c["score"] for c in chunks) >= RAG_MIN_SCORE:
        answer = pipeline.generator.generate(question, chunks)
        return {
            "answer": clean_for_speech(answer),
            "mode": "knowledge_base",
            "sources": [{"title": s, "url": None}
                        for s in sorted({c["source"] for c in chunks})],
        }

    # 2) Fall back to trusted web search
    results = web_search(question)
    if not results:
        return {"answer": NO_ANSWER, "mode": "none", "sources": []}

    answer = answer_from_web(pipeline, question, results)
    return {
        "answer": clean_for_speech(answer) or NO_ANSWER,
        "mode": "web",
        "sources": [{"title": r["title"], "url": r["url"]} for r in results[:3]],
    }


@router.get("/voice", response_class=HTMLResponse)
async def voice_page(request: Request):
    return templates.TemplateResponse(request, "voice_assistant.html")


@router.post("/voice/api")
async def voice_api(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid request."}, status_code=400)

    question = str(body.get("question", "")).strip()
    if not question:
        return JSONResponse({"error": "I did not catch that. Please try again."}, status_code=400)
    if len(question) > MAX_QUESTION_CHARS:
        return JSONResponse({"error": "That question is too long."}, status_code=400)

    try:
        return await run_in_threadpool(handle_question, question)
    except Exception:
        logger.exception("Voice request failed")
        return JSONResponse(
            {"error": "Sorry, the assistant is unavailable right now."},
            status_code=500,
        )