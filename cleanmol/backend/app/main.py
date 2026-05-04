from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import queue
import threading
import json
from pathlib import Path
from .pipeline import run_pipeline
from .model_config import resolve_latest_model_defaults
from .discovery_automation import run_discovery_automation
from .online_source_catalog import search_huggingface_sources, source_catalog

app = FastAPI(title="CleanMol Backend", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunPayload(BaseModel):
    input_dir: str
    output_dir: str
    models: Dict[str, str]
    keys: Dict[str, str]
    options: Optional[Dict[str, Any]] = None


class DiscoveryPayload(BaseModel):
    output_dir: str
    uploaded_dataset_path: Optional[str] = None
    keys: Optional[Dict[str, str]] = None
    options: Optional[Dict[str, Any]] = None


class SourceSearchPayload(BaseModel):
    query: str
    limit: Optional[int] = 12
    keys: Optional[Dict[str, str]] = None


class DefaultsResolvePayload(BaseModel):
    keys: Optional[Dict[str, str]] = None

@app.get("/")
def root():
    return {"status": "CleanMol backend is running", "version": "1.0"}


@app.get("/api/defaults")
def api_defaults():
    return resolve_latest_model_defaults({})


@app.post("/api/defaults/resolve")
def api_resolve_defaults(payload: DefaultsResolvePayload):
    return resolve_latest_model_defaults(payload.keys or {})


@app.get("/api/discovery/sources")
def api_discovery_sources():
    catalog = source_catalog()
    catalog["upload_supported"] = [".csv", ".tsv", ".xlsx", ".xlsm"]
    return catalog


@app.get("/api/discovery/source-catalog")
def api_discovery_source_catalog():
    return api_discovery_sources()


@app.post("/api/discovery/source-search")
def api_discovery_source_search(payload: SourceSearchPayload):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Search query is required")
    token = (payload.keys or {}).get("hf") or (payload.keys or {}).get("huggingface") or ""
    return search_huggingface_sources(payload.query, limit=payload.limit or 12, token=token)


def _safe_upload_name(filename: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in filename)
    return safe or "uploaded_dataset.csv"


@app.post("/api/discovery/upload-dataset")
async def api_discovery_upload_dataset(
    output_dir: str = Form(...),
    file: UploadFile = File(...),
):
    target_dir = Path(output_dir) / "discovery_uploads"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / _safe_upload_name(file.filename or "uploaded_dataset.csv")
    with target.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return {"ok": True, "path": str(target)}

@app.post("/api/run")
def api_run(payload: RunPayload):
    try:
        info = run_pipeline(
            input_dir=payload.input_dir,
            output_dir=payload.output_dir,
            models=payload.models,
            keys=payload.keys,
            options=payload.options or {},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    ok = (info.get("run", {}).get("status") == "ok")
    return {
        "ok": ok,
        "run": info,
        "log_file": info.get("log_file")
    }


@app.post("/api/discovery/run")
def api_discovery_run(payload: DiscoveryPayload):
    try:
        result = run_discovery_automation(
            output_dir=payload.output_dir,
            uploaded_dataset_path=payload.uploaded_dataset_path,
            keys=payload.keys or {},
            options=payload.options or {},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return result


@app.post("/api/discovery/run-stream")
async def api_discovery_run_stream(payload: DiscoveryPayload):
    """Run automated discovery with streaming progress updates via SSE."""
    progress_queue: queue.Queue = queue.Queue()

    def progress_callback(msg: str):
        progress_queue.put(msg)

    def generate():
        result_holder = {}

        def run_discovery_thread():
            try:
                result = run_discovery_automation(
                    output_dir=payload.output_dir,
                    uploaded_dataset_path=payload.uploaded_dataset_path,
                    keys=payload.keys or {},
                    options=payload.options or {},
                    progress_callback=progress_callback,
                )
                result_holder["result"] = result
            except Exception as e:
                result_holder["error"] = str(e)
            finally:
                progress_queue.put(None)

        thread = threading.Thread(target=run_discovery_thread, daemon=True)
        thread.start()

        try:
            while True:
                try:
                    msg = progress_queue.get(timeout=1.0)
                    if msg is None:
                        break
                    if msg.startswith("{"):
                        yield f"data: {msg}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'progress', 'message': msg})}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except GeneratorExit:
            pass

        thread.join(timeout=5)

        if "error" in result_holder:
            yield f"data: {json.dumps({'type': 'error', 'error': result_holder['error']})}\n\n"
        elif "result" in result_holder:
            yield f"data: {json.dumps({'type': 'discovery_complete', 'result': result_holder['result']})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/run-stream")
async def api_run_stream(payload: RunPayload):
    """Run pipeline with streaming progress updates via SSE."""
    progress_queue: queue.Queue = queue.Queue()

    def progress_callback(msg: str):
        progress_queue.put(msg)

    def generate():
        result_holder = {}

        def run_pipeline_thread():
            try:
                result = run_pipeline(
                    input_dir=payload.input_dir,
                    output_dir=payload.output_dir,
                    models=payload.models,
                    keys=payload.keys,
                    options=payload.options or {},
                    progress_callback=progress_callback
                )
                result_holder["result"] = result
            except Exception as e:
                result_holder["error"] = str(e)
            finally:
                progress_queue.put(None)  # Signal completion

        thread = threading.Thread(target=run_pipeline_thread, daemon=True)
        thread.start()

        try:
            while True:
                try:
                    msg = progress_queue.get(timeout=1.0)
                    if msg is None:
                        break
                    # Check if already JSON (structured progress)
                    if msg.startswith("{"):
                        yield f"data: {msg}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'progress', 'message': msg})}\n\n"
                except queue.Empty:
                    # Heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except GeneratorExit:
            # Client disconnected
            pass

        thread.join(timeout=5)

        if "error" in result_holder:
            yield f"data: {json.dumps({'type': 'error', 'error': result_holder['error']})}\n\n"
        elif "result" in result_holder:
            yield f"data: {json.dumps({'type': 'complete', 'result': result_holder['result']})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
