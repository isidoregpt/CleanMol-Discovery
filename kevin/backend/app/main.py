from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import queue
import threading
import json
from .pipeline import run_pipeline

app = FastAPI(title="Kevin Backend", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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

@app.get("/")
def root():
    return {"status": "Kevin backend is running", "version": "1.0"}

@app.post("/api/run")
def api_run(payload: RunPayload):
    info = run_pipeline(
        input_dir=payload.input_dir,
        output_dir=payload.output_dir,
        models=payload.models,
        keys=payload.keys,
        options=payload.options or {},
    )
    ok = (info.get("run", {}).get("status") == "ok")
    return {
        "ok": ok,
        "run": info,
        "log_file": info.get("log_file")
    }


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
