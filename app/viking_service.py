import json
import os
import threading
from pathlib import Path
from typing import Optional

import openviking as ov

from .snippet import CandidateDoc, select_snippet

'''viking 服务的 api'''

class VikingService:
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.state_file = self.workspace_root / "service_state.json"
        self.agent_dir = self.workspace_root / "uploaded_agents"
        self.agent_dir.mkdir(parents=True, exist_ok=True)

        config_file = os.getenv("OPENVIKING_CONFIG_FILE", str(self.workspace_root / "ov.conf"))
        self.client = ov.SyncOpenViking(config_file=config_file)
        self.client.initialize()

        self.lock = threading.Lock()
        self.path_to_uri: dict[str, str] = {}
        self._load_state()

    def close(self) -> None:
        self.client.close()

    def _normalize_path(self, folder_path: str) -> str:
        p = Path(folder_path).expanduser().resolve()
        return str(p)

    def _load_state(self) -> None:
        if not self.state_file.exists():
            return
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            self.path_to_uri = data.get("path_to_uri", {})
        except Exception:
            self.path_to_uri = {}

    def _save_state(self) -> None:
        payload = {"path_to_uri": self.path_to_uri}
        self.state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def register_resource(self, folder_path: str) -> tuple[str, str, str]:
        normalized = self._normalize_path(folder_path)
        p = Path(normalized)
        if not p.exists() or not p.is_dir():
            raise ValueError("folder_path must be an existing directory")

        with self.lock:
            if normalized in self.path_to_uri:
                return normalized, self.path_to_uri[normalized], "already_uploaded"

            result = self.client.add_resource(path=normalized)
            self.client.wait_processed()

            resource_uri = None
            if isinstance(result, dict):
                resource_uri = result.get("root_uri") or result.get("uri")
            if not resource_uri:
                resource_uri = f"viking://resources/{Path(normalized).name}"

            self.path_to_uri[normalized] = resource_uri
            self._save_state()
            return normalized, resource_uri, "uploaded"

    def list_resources(self) -> list[str]:
        return sorted(self.path_to_uri.keys())

    def create_session(self) -> str:
        data = self.client.create_session()
        if isinstance(data, dict):
            sid = data.get("session_id") or data.get("id")
            if sid:
                return sid
        raise RuntimeError("Failed to create session")

    def commit_session(self, session_id: str) -> None:
        self.client.commit_session(session_id)

    def upload_agent(self, filename: str, content: bytes) -> str:
        save_path = self.agent_dir / Path(filename).name
        save_path.write_bytes(content)

        payload = None
        if save_path.suffix.lower() == ".json":
            try:
                payload = json.loads(content.decode("utf-8"))
            except Exception:
                payload = {"filename": save_path.name, "raw": content.decode("utf-8", errors="ignore")}
        else:
            payload = {"filename": save_path.name, "raw": content.decode("utf-8", errors="ignore")}

        self.client.add_skill(payload, wait=True)
        return str(save_path)

    def query(self, query: str, session_id: Optional[str], folder_path: Optional[str], top_k: int, commit_after_response: bool) -> tuple[str, str, bool]:
        sid = session_id or self.create_session()

        self.client.add_message(session_id=sid, role="user", content=query)

        target_uri = ""
        if folder_path:
            normalized = self._normalize_path(folder_path)
            target_uri = self.path_to_uri.get(normalized, "")

        query_lower = query.lower()
        code_like = any(k in query_lower for k in ["代码", "代码片段", "接口", "add_resource", "file_path", "路径", "地址"])
        html_like = any(k in query_lower for k in ["html", "前端", "页面", "js", "javascript"])
        python_like = any(k in query_lower for k in ["python", ".py", "py代码", "python代码"]) or (code_like and not html_like)

        result = self.client.find(query, target_uri=target_uri, limit=top_k)
        resources = list(getattr(result, "resources", []))

        if python_like and target_uri:
            try:
                py_matches = self.client.glob(pattern="**/*.py", uri=target_uri).get("matches", [])
                existing = {getattr(r, "uri", "") for r in resources}
                for uri in py_matches[:30]:
                    if uri not in existing:
                        resources.append(type("R", (), {"uri": uri, "score": 0.0})())
            except Exception:
                pass

        def _is_meta_uri(uri: str) -> bool:
            name = uri.rsplit("/", 1)[-1].lower()
            return name in {".overview.md", ".abstract.md"} or name.startswith(".")

        non_meta = [r for r in resources if not _is_meta_uri(getattr(r, "uri", ""))]
        selected_resources = non_meta if non_meta else resources

        docs = []
        for r in selected_resources:
            try:
                content = self.client.read(r.uri)
                docs.append(CandidateDoc(uri=r.uri, score=float(r.score), content=content))
            except Exception:
                continue

        snippet = select_snippet(query, docs)

        if snippet:
            self.client.add_message(session_id=sid, role="assistant", content=snippet)
        else:
            snippet = ""

        committed = False
        if commit_after_response:
            self.client.commit_session(sid)
            committed = True

        return sid, snippet, committed
