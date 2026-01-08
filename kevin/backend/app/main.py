from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
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
    return {"ok": ok, "run": info}
