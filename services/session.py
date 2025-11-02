"""Simple file-backed session store for chat interactions.

Each session is a JSON file under data/sessions/<session_id>.json with structure:
{ "id": <id>, "created_at": <iso>, "interactions": [ {"role":"user","question":..., "metadata":...}, {"role":"ai","response":..., "metadata":...} ] }
"""
import os
import json
from datetime import datetime
from typing import Optional

SESSIONS_DIR = os.path.join("data", "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)


def _session_path(session_id: str) -> str:
    return os.path.join(SESSIONS_DIR, f"{session_id}.json")


def create_session(session_id: str) -> dict:
    path = _session_path(session_id)
    now = datetime.utcnow().isoformat() + "Z"
    data = {"id": session_id, "created_at": now, "interactions": []}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def get_session(session_id: str) -> Optional[dict]:
    path = _session_path(session_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def append_interaction(session_id: str, role: str, payload: dict) -> dict:
    path = _session_path(session_id)
    s = get_session(session_id)
    if s is None:
        s = create_session(session_id)
    s.setdefault("interactions", []).append({"role": role, "payload": payload, "ts": datetime.utcnow().isoformat() + "Z"})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    return s
