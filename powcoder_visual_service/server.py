from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from powcoder_visual import state as visual_state  # noqa: E402

STATIC_DIR = ROOT / "powcoder_dashboard"
LEGACY_STATE_FILE = Path("/tmp/xiaozhi-dispatcher-state.json")
LEGACY_RUNS_DIR = Path("/tmp/xiaozhi-dispatcher-runs")
LEGACY_TERMINAL_TTL_SECONDS = 300
ACTIVE_STATUSES = {"pending", "accepted", "running"}


def _read_json(path: Path, fallback):
    try:
        if not path.exists():
            return fallback
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _is_recent_terminal_legacy(path: Path, status: str) -> bool:
    if status in ACTIVE_STATUSES:
        return True
    try:
        return time.time() - path.stat().st_mtime <= LEGACY_TERMINAL_TTL_SECONDS
    except OSError:
        return False


def _legacy_worker_from_state() -> dict | None:
    legacy = _read_json(LEGACY_STATE_FILE, {})
    if not legacy:
        return None
    backend = legacy.get("backend") or legacy.get("tool") or "dispatcher"
    run_id = legacy.get("run_id") or "legacy_latest"
    status = legacy.get("status") or "idle"
    if not _is_recent_terminal_legacy(LEGACY_STATE_FILE, status):
        return None
    return {
        "worker_id": f"legacy_{backend}",
        "kind": backend,
        "display_name": str(backend).title(),
        "agent_id": legacy.get("agent_id", ""),
        "status": status,
        "task": legacy.get("task", ""),
        "run_id": run_id,
        "started_at": legacy.get("started"),
        "finished_at": legacy.get("finished"),
        "last_message": status,
        "result_preview": (legacy.get("result") or "")[:500],
    }


def _legacy_sessions() -> list[dict]:
    sessions = []
    if not LEGACY_RUNS_DIR.exists():
        return sessions
    for path in sorted(LEGACY_RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]:
        item = _read_json(path, {})
        if not item:
            continue
        status = item.get("status", "idle")
        if not _is_recent_terminal_legacy(path, status):
            continue
        sessions.append(
            {
                "session_id": item.get("run_id") or path.stem,
                "type": "task",
                "title": (item.get("task") or path.stem)[:50],
                "status": status,
                "created_at": item.get("started", ""),
            }
        )
    return sessions


def _merged_state() -> dict:
    data = visual_state.read_state()
    worker = _legacy_worker_from_state()
    if worker and not data.get("workers"):
        data["workers"] = [worker]
    if not data.get("sessions"):
        data["sessions"] = _legacy_sessions()
    return data


async def api_state(_: Request) -> JSONResponse:
    return JSONResponse(_merged_state())


async def api_sessions(_: Request) -> JSONResponse:
    state = _merged_state()
    return JSONResponse({"sessions": state.get("sessions", [])})


async def api_session(request: Request) -> JSONResponse:
    session_id = request.path_params["session_id"]
    session_file = visual_state.SESSIONS_DIR / f"{session_id}.json"
    data = _read_json(session_file, {})
    if not data:
        for session in _merged_state().get("sessions", []):
            if session.get("session_id") == session_id:
                data = session
                break
    if not data:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(data)


async def api_events(request: Request) -> JSONResponse:
    after_seq = int(request.query_params.get("after_seq", "0") or "0")
    events = []
    if visual_state.EVENTS_FILE.exists():
        for line in visual_state.EVENTS_FILE.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if int(item.get("seq") or 0) > after_seq:
                events.append(item)
    return JSONResponse({"events": events[-200:]})


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "service": "powcoder-visual"})


routes = [
    Route("/health", health, methods=["GET"]),
    Route("/api/state", api_state, methods=["GET"]),
    Route("/api/sessions", api_sessions, methods=["GET"]),
    Route("/api/sessions/{session_id}", api_session, methods=["GET"]),
    Route("/api/events", api_events, methods=["GET"]),
    Mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="dashboard"),
]

app = Starlette(routes=routes)


if __name__ == "__main__":
    import uvicorn

    port = int(__import__("os").environ.get("PORT", "9200"))
    uvicorn.run(app, host="0.0.0.0", port=port)
