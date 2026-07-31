import os
import sys
import uuid
import time
import logging
from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.config import LOGS_DIR, ALLOWED_ORIGINS
from backend.pipeline import PipelineOrchestrator

app = FastAPI(title="Nexus.ai CI Debug Agent API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """
    Endpoint for Render deployment verification and health checks.
    """
    return {"status": "healthy"}


# Global in-memory store for analysis runs
runs: Dict[str, Dict[str, Any]] = {}

class AnalyzeRequest(BaseModel):
    log_id: str

class FixRequest(BaseModel):
    run_id: str
    fix_index: int = 0

# Custom orchestrator subclass to capture stage updates and logs
class ApiPipelineOrchestrator(PipelineOrchestrator):
    def __init__(self, run_id: str, on_stage_update, on_log):
        super().__init__()
        self.run_id = run_id
        self.on_stage_update = on_stage_update
        self.on_log = on_log

    def _execute_stage(self, stage_name: str, func, *args, **kwargs) -> Any:
        self.on_stage_update(self.run_id, stage_name, "RUNNING", 0.0)
        self.on_log(self.run_id, "INFO", f"[{stage_name}] Starting stage execution...")
        start_time = time.time()
        try:
            result = super()._execute_stage(stage_name, func, *args, **kwargs)
            duration = time.time() - start_time
            self.on_stage_update(self.run_id, stage_name, "SUCCESS", duration)
            self.on_log(self.run_id, "INFO", f"[{stage_name}] Completed successfully in {duration:.2f}s.")
            return result
        except Exception as e:
            duration = time.time() - start_time
            self.on_stage_update(self.run_id, stage_name, "FAILED", duration)
            self.on_log(self.run_id, "ERROR", f"[{stage_name}] Failed after {duration:.2f}s: {str(e)}")
            raise e

# Custom logging handler to redirect backend logs to run console logs
class RunLogHandler(logging.Handler):
    def __init__(self, run_id: str, on_log):
        super().__init__()
        self.run_id = run_id
        self.on_log = on_log

    def emit(self, record):
        try:
            msg = self.format(record)
            self.on_log(self.run_id, record.levelname, msg)
        except Exception:
            self.handleError(record)

def update_stage_status(run_id: str, stage_name: str, status: str, duration: float):
    if run_id in runs:
        runs[run_id]["stages"][stage_name] = {
            "status": status,
            "time": duration
        }

def append_run_log(run_id: str, level: str, message: str):
    if run_id in runs:
        timestamp = time.strftime("%H:%M:%S")
        runs[run_id]["console_logs"].append({
            "timestamp": timestamp,
            "level": level,
            "message": message
        })

def run_analysis_thread(run_id: str, log_path: str):
    logger = logging.getLogger("backend")
    handler = RunLogHandler(run_id, append_run_log)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    
    try:
        runs[run_id]["status"] = "running"
        orchestrator = ApiPipelineOrchestrator(run_id, update_stage_status, append_run_log)
        
        # Run orchestrator
        report = orchestrator.run(log_path)
        
        # Prepare report dict
        report_dict = {
            "pipeline_error": report.pipeline_error,
            "failure_type": report.failure_type,
            "root_cause": report.root_cause,
            "explanation": report.explanation,
            "evidence": report.evidence,
            "suggested_fixes": report.suggested_fixes,
            "original_confidence": report.original_confidence,
            "final_confidence": report.final_confidence,
            "critic_status": report.critic_status,
            "critic_comments": report.critic_comments
        }
        
        runs[run_id]["status"] = "completed"
        runs[run_id]["report"] = report_dict
        append_run_log(run_id, "INFO", "Analysis completed successfully. Report generated.")
    except Exception as e:
        runs[run_id]["status"] = "failed"
        runs[run_id]["error"] = str(e)
        append_run_log(run_id, "ERROR", f"Analysis failed: {str(e)}")
    finally:
        logger.removeHandler(handler)

@app.get("/api/logs")
def get_logs():
    """
    Returns available logs for analysis (both sample_logs and uploaded logs).
    """
    logs = []
    
    # 1. Walk sample logs
    sample_logs_dir = os.path.join(project_root, "backend", "sample_logs")
    if os.path.exists(sample_logs_dir):
        for root, dirs, files in os.walk(sample_logs_dir):
            for file in files:
                if file.endswith((".txt", ".log", ".zip")):
                    rel_path = os.path.relpath(os.path.join(root, file), sample_logs_dir)
                    # Create user-friendly title
                    name = rel_path.replace("\\", " / ")
                    if "django" in name.lower():
                        name = "Django Test Run Failure"
                    elif "react" in name.lower():
                        name = "React Build System Failure"
                    elif "vscode" in name.lower():
                        name = "VS Code Integration Test Failure"
                    
                    logs.append({
                        "id": f"sample:{rel_path}",
                        "name": name,
                        "filename": file,
                        "type": "sample"
                    })
                    
    # 2. Walk uploaded logs
    uploaded_logs_dir = LOGS_DIR
    if os.path.exists(uploaded_logs_dir):
        for file in os.listdir(uploaded_logs_dir):
            if file.endswith((".txt", ".log", ".zip")) and not file.startswith("."):
                logs.append({
                    "id": f"uploaded:{file}",
                    "name": f"Uploaded Log: {file}",
                    "filename": file,
                    "type": "uploaded"
                })
                
    return logs

@app.post("/api/upload")
async def upload_log(file: UploadFile = File(...)):
    """
    Allows user to upload a custom log file.
    """
    if not file.filename.endswith((".txt", ".log", ".zip")):
        raise HTTPException(status_code=400, detail="Only .txt, .log, or .zip files are supported.")
        
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(LOGS_DIR, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    return {
        "log_id": f"uploaded:{filename}",
        "filename": file.filename,
        "name": f"Uploaded Log: {file.filename}"
    }

@app.post("/api/analyze")
def analyze_log(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Starts the analysis for the given log ID.
    """
    log_id = request.log_id
    
    # Resolve log path
    if log_id.startswith("sample:"):
        rel_path = log_id.split("sample:")[1]
        log_path = os.path.join(project_root, "backend", "sample_logs", rel_path)
    elif log_id.startswith("uploaded:"):
        filename = log_id.split("uploaded:")[1]
        log_path = os.path.join(LOGS_DIR, filename)
    else:
        raise HTTPException(status_code=400, detail="Invalid log ID format.")
        
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Log file not found.")
        
    run_id = str(uuid.uuid4())
    
    # Initialize run status
    runs[run_id] = {
        "run_id": run_id,
        "status": "pending",
        "log_name": os.path.basename(log_path),
        "stages": {
            stage: {"status": "PENDING", "time": 0.0}
            for stage in [
                "Parser", "Classifier", "Planner", "Collector", "Chunker",
                "Embedder", "Vector Store", "Retriever", "LLM", "Critic", "Report"
            ]
        },
        "console_logs": [],
        "report": None,
        "error": None
    }
    
    background_tasks.add_task(run_analysis_thread, run_id, log_path)
    
    return {"run_id": run_id}

@app.get("/api/runs/{run_id}")
def get_run_status(run_id: str):
    """
    Fetches progress and report for a run.
    """
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found.")
    return runs[run_id]

@app.post("/api/fix")
def apply_fix(request: FixRequest):
    """
    Simulates applying the suggested fix.
    """
    run_id = request.run_id
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found.")
        
    # Mocking remediation response
    return {
        "status": "success",
        "message": f"Fix #{request.fix_index + 1} has been applied successfully. Staging build verified: stable."
    }

if __name__ == "__main__":
    import uvicorn
    # Suppress sentence-transformers/huggingface logs to keep console clean
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
