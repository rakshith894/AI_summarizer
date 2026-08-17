"""
Text extraction utilities for the AI Summarizer.

Handles pulling plain text out of:
- Uploaded PDF files
- Uploaded DOCX files
- Uploaded plain text files
- Web page URLs (article-focused extraction, strips nav/ads/footers)
"""

import io
import re

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document


class ExtractionError(Exception):
    """Raised when text can't be extracted from a file or URL."""


def extract_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
    except Exception as e:
        raise ExtractionError(f"Could not read PDF: {e}")

    if not text:
        raise ExtractionError(
            "No extractable text found in this PDF (it may be a scanned image)."
        )
    return text


def extract_from_docx(file_bytes: bytes) -> str:
    try:
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception as e:
        raise ExtractionError(f"Could not read DOCX: {e}")

    if not text:
        raise ExtractionError("No text found in this document.")
    return text


def extract_from_txt(file_bytes: bytes) -> str:
    try:
        text = file_bytes.decode("utf-8", errors="ignore").strip()
    except Exception as e:
        raise ExtractionError(f"Could not read text file: {e}")

    if not text:
        raise ExtractionError("This file appears to be empty.")
    return text


def extract_from_file(filename: str, file_bytes: bytes) -> str:
    """Route to the right extractor based on file extension."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_from_pdf(file_bytes)
    if lower.endswith(".docx"):
        return extract_from_docx(file_bytes)
    if lower.endswith(".txt") or lower.endswith(".md"):
        return extract_from_txt(file_bytes)
    raise ExtractionError(
        "Unsupported file type. Please upload a .pdf, .docx, .txt, or .md file."
    )


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AISummarizerBot/1.0; "
        "+https://example.com/bot)"
    )
}

# Tags that are never part of readable article content.
_STRIP_TAGS = [
    "script", "style", "nav", "header", "footer", "aside",
    "form", "noscript", "svg", "iframe", "button",
]


def extract_from_url(url: str) -> str:
    """Fetch a URL and extract the main readable text, skipping nav/ads/footers."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ExtractionError(f"Could not fetch URL: {e}")

    content_type = resp.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        raise ExtractionError("That URL doesn't point to a readable web page.")

    soup = BeautifulSoup(resp.text, "lxml")

    for tag in soup(_STRIP_TAGS):
        tag.decompose()

    # Prefer <article> or <main> if present — usually the actual content,
    # skipping sidebars/menus that surround it.
    container = soup.find("article") or soup.find("main") or soup.body or soup

    text = container.get_text(separator="\n")
    # Collapse excess blank lines/whitespace left behind by stripped tags.
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    text = re.sub(r"[ \t]+", " ", text)

    if not text:
        raise ExtractionError("Could not extract readable article text from that page.")
    return text