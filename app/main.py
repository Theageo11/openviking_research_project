from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import (
    AgentUploadResponse,
    CommitResponse,
    CreateSessionResponse,
    ListResourcesResponse,
    QueryRequest,
    QueryResponse,
    RegisterResourceRequest,
    RegisterResourceResponse,
)
from .viking_service import VikingService

'''api封装，启动UI'''

ROOT = Path(__file__).resolve().parents[1]
service = VikingService(str(ROOT))

app = FastAPI(title="OpenViking Snippet Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/resources/register", response_model=RegisterResourceResponse)
def register_resource(req: RegisterResourceRequest):
    try:
        folder_path, uri, status = service.register_resource(req.folder_path)
        message = "folder already uploaded, skipped" if status == "already_uploaded" else "folder uploaded"
        return RegisterResourceResponse(status=status, folder_path=folder_path, resource_uri=uri, message=message)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/resources", response_model=ListResourcesResponse)
def list_resources():
    return ListResourcesResponse(uploaded_folders=service.list_resources())


@app.post("/api/sessions", response_model=CreateSessionResponse)
def create_session():
    try:
        sid = service.create_session()
        return CreateSessionResponse(session_id=sid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/commit", response_model=CommitResponse)
def commit_session(session_id: str):
    try:
        service.commit_session(session_id)
        return CommitResponse(session_id=session_id, status="committed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/agents/upload", response_model=AgentUploadResponse)
async def upload_agent(file: UploadFile = File(...)):
    try:
        content = await file.read()
        path = service.upload_agent(file.filename, content)
        return AgentUploadResponse(filename=file.filename, status="uploaded", message=f"saved: {path}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/query", response_model=QueryResponse)
def query(req: QueryRequest):
    try:
        sid, snippet, committed = service.query(
            query=req.query,
            session_id=req.session_id,
            folder_path=req.folder_path,
            top_k=req.top_k,
            commit_after_response=req.commit_after_response,
        )
        return QueryResponse(session_id=sid, snippet=snippet, committed=committed)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


frontend_dir = ROOT / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
