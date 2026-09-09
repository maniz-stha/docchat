# DocChat

Ask focused questions of uploaded documents and receive a researched answer with a verification report.

Try it at [https://docchat.shresthamanis.com.np](https://docchat.shresthamanis.com.np).

## How it works

1. Upload PDF, DOCX, TXT, or Markdown files (up to 50 MB each; 200 MB total).
2. DocChat extracts and caches document chunks, then combines keyword and semantic retrieval to find relevant passages.
3. IBM watsonx generates an answer from those passages.
4. A second model pass checks support, contradictions, and relevance; the research is retried once when the check fails.

The app keeps document retrieval in the current browser session. Starting a new session clears that session’s in-memory retriever.

## Run locally

Create a `.env` file with your IBM watsonx credentials:

```env
WATSONX_API_KEY=your-api-key
WATSONX_URL=your-watsonx-url
WATSONX_PROJECT_ID=your-project-id
```

Install dependencies and start the server:

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Open <http://127.0.0.1:8000>.

## API

- `POST /api/ask` accepts a `question` and one or more `files`, then returns an answer, verification report, and source names.
- `DELETE /api/session` starts a fresh browser session.
