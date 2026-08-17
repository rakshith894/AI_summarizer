"""
AI Summarizer - FastAPI backend.

Architecture:
    User -> FastAPI/UI -> LLM API -> Prompt -> Summary

Run locally with:
    uvicorn main:app --reload
Then open http://127.0.0.1:8000
"""

import os
import logging

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, HttpUrl
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from prompt import build_prompt
from text_extract import extract_from_file, extract_from_url, ExtractionError

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()  # reads .env into environment variables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-summarizer")

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    logger.warning("GEMINI_API_KEY is not set. Requests to /summarize will fail.")

client = (
    OpenAI(
        api_key=API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    if API_KEY
    else None
)

MODEL_NAME = "gemini-2.5-flash-lite"
MAX_INPUT_CHARS = 50_000  # guard against runaway costs / huge payloads

app = FastAPI(title="AI Summarizer", version="1.0.0")

# Allow the simple frontend (or any frontend during dev) to call the API.
# Lock this down to specific origins before deploying to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the simple HTML/JS frontend from /static
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to summarize")
    length: str = Field("short", description="short | medium | detailed")
    style: str = Field("paragraph", description="paragraph | bullets | one-liner")


class SummarizeResponse(BaseModel):
    summary: str
    input_chars: int
    model: str


class UrlExtractRequest(BaseModel):
    url: HttpUrl


class ExtractResponse(BaseModel):
    text: str
    chars: int
    truncated: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def serve_ui():
    """Serve the simple frontend page."""
    return FileResponse("static/index.html")


@app.get("/health")
def health_check():
    """Basic health check — useful once deployed."""
    return {"status": "ok", "llm_configured": client is not None}


MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@app.post("/extract-file", response_model=ExtractResponse)
async def extract_file(file: UploadFile = File(...)):
    """
    Extract plain text from an uploaded PDF, DOCX, or TXT/MD file.
    Returns the extracted text for the frontend to drop into the textarea.
    """
    file_bytes = await file.read()

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds the 10 MB upload limit.")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        text = extract_from_file(file.filename or "upload", file_bytes)
    except ExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    truncated = False
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]
        truncated = True

    return ExtractResponse(text=text, chars=len(text), truncated=truncated)


@app.post("/extract-url", response_model=ExtractResponse)
def extract_url(payload: UrlExtractRequest):
    """
    Fetch a URL and extract the main readable text (article body),
    skipping navigation, ads, and footers where possible.
    """
    try:
        text = extract_from_url(str(payload.url))
    except ExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    truncated = False
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]
        truncated = True

    return ExtractResponse(text=text, chars=len(text), truncated=truncated)


@app.post("/summarize", response_model=SummarizeResponse)
def summarize(payload: SummarizeRequest):
    """
    Core endpoint: validates input, builds the prompt,
    calls the LLM, and returns the summary.
    """
    if client is None:
        raise HTTPException(
            status_code=500,
            detail="Server is not configured with a GEMINI_API_KEY.",
        )

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="`text` must not be empty.")

    if len(text) > MAX_INPUT_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"`text` exceeds max length of {MAX_INPUT_CHARS} characters.",
        )

    if payload.length not in ("short", "medium", "detailed"):
        raise HTTPException(status_code=400, detail="Invalid `length` option.")

    if payload.style not in ("paragraph", "bullets", "one-liner"):
        raise HTTPException(status_code=400, detail="Invalid `style` option.")

    prompt = build_prompt(text, length=payload.length, style=payload.style)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        summary_text = response.choices[0].message.content.strip()
    except OpenAIError as e:
        logger.error(f"LLM API error: {e}")
        raise HTTPException(status_code=502, detail=f"The summarization service failed: {e}")

    return SummarizeResponse(
        summary=summary_text,
        input_chars=len(text),
        model=MODEL_NAME,
    )