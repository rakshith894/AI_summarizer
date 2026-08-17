# AI Summarizer

Simple pipeline: **User → FastAPI/UI → Prompt → LLM API → Summary**

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then add your real GEMINI_API_KEY (get one free at aistudio.google.com)
```

## Run

```bash
uvicorn main:app --reload
```

Open **http://127.0.0.1:8000** for the UI, or **http://127.0.0.1:8000/docs** for the interactive API docs.

## Input methods

The UI supports three ways to get text in:
- **Paste** — type or paste directly
- **Upload a file** — PDF, DOCX, TXT, or MD (max 10 MB)
- **From a URL** — fetches the page and extracts the main readable text

## API

`POST /extract-file` — multipart form upload (`file` field). Returns `{ text, chars, truncated }`.

`POST /extract-url`
```json
{ "url": "https://example.com/article" }
```
Returns `{ text, chars, truncated }`.

`POST /summarize`

```json
{
  "text": "Long text here...",
  "length": "short",     // short | medium | detailed
  "style": "paragraph"   // paragraph | bullets | one-liner
}
```

Response:

```json
{
  "summary": "...",
  "input_chars": 1234,
  "model": "gemini-2.5-flash-lite"
}
```

## Deploy with Docker

```bash
docker build -t ai-summarizer .
docker run -p 8000:8000 --env-file .env ai-summarizer
```

## Next steps (optional extras)

- Caching to avoid re-summarizing identical input
- Rate limiting to control API costs