import hashlib
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agents.workflow import AgentWorkflow
from config import constants
from document_processor.file_handler import DocumentProcessor
from retriever.builder import RetrieverBuilder
from utils.logging import logger


ROOT = Path(__file__).parent
app = FastAPI(title="DocChat")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

processor = DocumentProcessor()
retriever_builder = RetrieverBuilder()
workflow = AgentWorkflow()
# ponytail: in-memory sessions reset on restart; use Redis only if multiple workers or durable sessions are needed.
sessions: Dict[str, Dict[str, Any]] = {}


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/how-it-works", response_class=FileResponse)
def how_it_works() -> FileResponse:
    return FileResponse(ROOT / "static" / "how-it-works.html")


@app.post("/api/ask")
async def ask(
    request: Request,
    question: str = Form(...),
    files: List[UploadFile] = File(...),
):
    if not question.strip():
        raise HTTPException(status_code=400, detail="Enter a question before asking.")
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one document.")

    invalid = [file.filename for file in files if Path(file.filename or "").suffix.lower() not in constants.ALLOWED_TYPES]
    if invalid:
        raise HTTPException(status_code=400, detail="Unsupported file type: " + ", ".join(invalid))

    session_id = request.cookies.get("docchat_session") or str(uuid.uuid4())
    state = sessions.setdefault(session_id, {"file_hashes": frozenset(), "retriever": None})

    try:
        with tempfile.TemporaryDirectory(prefix="docchat-") as directory:
            uploaded_files = await _save_uploads(files, Path(directory))
            current_hashes = _get_file_hashes(uploaded_files)

            if state["retriever"] is None or current_hashes != state["file_hashes"]:
                chunks = processor.process(uploaded_files)
                if not chunks:
                    raise ValueError("No readable content was found in the uploaded documents.")
                state.update({
                    "file_hashes": current_hashes,
                    "retriever": retriever_builder.build_hybrid_retriever(chunks),
                })

            result = workflow.full_pipeline(question=question, retriever=state["retriever"])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Processing error")
        raise HTTPException(status_code=500, detail="Unable to answer that question. Please try again.") from error

    response = JSONResponse({
        "answer": result["draft_answer"],
        "verification": result["verification_report"],
        "sources": [Path(file.filename or "document").name for file in files],
    })
    response.set_cookie("docchat_session", session_id, httponly=True, samesite="lax")
    return response


@app.delete("/api/session")
def reset_session(request: Request):
    sessions.pop(request.cookies.get("docchat_session"), None)
    response = JSONResponse({"ok": True})
    response.delete_cookie("docchat_session")
    return response


async def _save_uploads(files: List[UploadFile], directory: Path) -> List[SimpleNamespace]:
    uploaded_files = []
    total_size = 0
    for index, file in enumerate(files):
        filename = Path(file.filename or f"document-{index}").name
        path = directory / f"{index}-{filename}"
        file_size = 0
        with open(path, "wb") as handle:
            while chunk := await file.read(1024 * 1024):
                file_size += len(chunk)
                total_size += len(chunk)
                if file_size > constants.MAX_FILE_SIZE:
                    raise ValueError(f"{filename} exceeds the {constants.MAX_FILE_SIZE // 1024 // 1024}MB file limit")
                if total_size > constants.MAX_TOTAL_SIZE:
                    raise ValueError(f"Total upload size exceeds {constants.MAX_TOTAL_SIZE // 1024 // 1024}MB")
                handle.write(chunk)
        uploaded_files.append(SimpleNamespace(name=str(path)))
    return uploaded_files


def _get_file_hashes(uploaded_files: List[SimpleNamespace]) -> frozenset:
    """Generate SHA-256 hashes for uploaded files."""
    hashes = set()
    for file in uploaded_files:
        with open(file.name, "rb") as handle:
            hashes.add(hashlib.sha256(handle.read()).hexdigest())
    return frozenset(hashes)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
