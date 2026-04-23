from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import fcntl
except Exception:  # pragma: no cover - Windows fallback
    fcntl = None


VISUAL_DIR = Path(os.environ.get("POWCODER_VISUAL_DIR", "/tmp/powcoder-visualizer"))
STATE_FILE = VISUAL_DIR / "state.json"
EVENTS_FILE = VISUAL_DIR / "events.jsonl"
SESSIONS_DIR = VISUAL_DIR / "sessions"
LOCK_FILE = VISUAL_DIR / ".lock"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    VISUAL_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def _locked():
    _ensure_dirs()
    with LOCK_FILE.open("a+") as lock:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _default_state() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": _now(),
        "active_conversation_id": "",
        "active_task_id": "",
        "mode": "idle",
        "connection": {
            "device_id": "",
            "source": "",
            "status": "offline",
        },
        "chat": {
            "provider": "JoyInside",
            "status": "idle",
            "last_user_text": "",
            "last_assistant_text": "",
        },
        "proposal": {
            "state": "none",
            "function_name": "",
            "task": "",
            "proposal_text": "",
        },
        "workers": [],
        "sessions": [],
        "last_event_seq": 0,
    }


def _read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        if not path.exists():
            return fallback
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else fallback
    except Exception:
        return fallback


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    _ensure_dirs()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def _merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    for key, value in patch.items():
        if (
            isinstance(value, dict)
            and isinstance(base.get(key), dict)
        ):
            _merge_dict(base[key], value)
        else:
            base[key] = value
    return base


def _upsert_session(state: dict[str, Any], session: dict[str, Any]) -> None:
    session_id = session.get("session_id")
    if not session_id:
        return
    sessions = state.setdefault("sessions", [])
    merged_session = session
    for idx, existing in enumerate(sessions):
        if existing.get("session_id") == session_id:
            merged = dict(existing)
            merged.update({k: v for k, v in session.items() if v not in (None, "")})
            sessions[idx] = merged
            merged_session = merged
            break
    else:
        sessions.insert(0, session)
    del sessions[30:]
    session_path = SESSIONS_DIR / f"{session_id}.json"
    session_path.write_text(
        json.dumps(merged_session, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _upsert_worker(state: dict[str, Any], worker: dict[str, Any]) -> None:
    worker_id = worker.get("worker_id")
    if not worker_id:
        return
    workers = state.setdefault("workers", [])
    for idx, existing in enumerate(workers):
        if existing.get("worker_id") == worker_id:
            merged = dict(existing)
            merged.update(worker)
            workers[idx] = merged
            break
    else:
        workers.append(worker)


def read_state() -> dict[str, Any]:
    _ensure_dirs()
    state = _default_state()
    state.update(_read_json(STATE_FILE, {}))
    return state


def write_state_patch(patch: dict[str, Any]) -> dict[str, Any]:
    with _locked():
        state = read_state()
        _merge_dict(state, patch)
        state["updated_at"] = _now()
        _atomic_write(STATE_FILE, state)
        return state


def append_event(event: str, payload: dict[str, Any] | None = None, **meta: Any) -> dict[str, Any]:
    payload = payload or {}
    with _locked():
        state = read_state()
        seq = int(state.get("last_event_seq") or 0) + 1
        state["last_event_seq"] = seq
        state["updated_at"] = _now()
        record = {
            "seq": seq,
            "ts": state["updated_at"],
            "event": event,
            "payload": payload,
        }
        record.update({k: v for k, v in meta.items() if v is not None})
        with EVENTS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        _atomic_write(STATE_FILE, state)
        return record


def set_connection(
    *,
    conversation_id: str,
    device_id: str | None = None,
    source: str = "browser",
    status: str = "connected",
) -> None:
    write_state_patch(
        {
            "active_conversation_id": conversation_id,
            "connection": {
                "device_id": device_id or "",
                "source": source,
                "status": status,
            },
        }
    )
    append_event(
        "conversation.updated",
        {
            "conversation_id": conversation_id,
            "device_id": device_id or "",
            "source": source,
            "status": status,
        },
        conversation_id=conversation_id,
    )


def set_mode(conversation_id: str, mode: str) -> None:
    write_state_patch(
        {
            "active_conversation_id": conversation_id,
            "mode": mode,
        }
    )
    append_event(
        "mode.changed",
        {"mode": mode},
        conversation_id=conversation_id,
    )


def update_conversation(
    conversation_id: str,
    *,
    mode: str = "auto",
    user_text: str = "",
    assistant_text: str = "",
    status: str = "idle",
    provider: str = "PowCoder",
    create_session: bool = True,
) -> None:
    mode = (mode or "auto").strip() or "auto"
    user_preview = (user_text or "")[:300]
    assistant_preview = (assistant_text or "")[:500]
    effective_status = status or ("serving" if user_preview and not assistant_preview else "idle")

    with _locked():
        state = read_state()
        state["active_conversation_id"] = conversation_id
        state["mode"] = mode
        if user_preview:
            state["last_user_text"] = user_preview
        if assistant_preview:
            state["last_assistant_text"] = assistant_preview

        if mode != "task":
            chat = state.setdefault("chat", {})
            chat["provider"] = provider or chat.get("provider") or "PowCoder"
            chat["status"] = effective_status
            if user_preview:
                chat["last_user_text"] = user_preview
            if assistant_preview:
                chat["last_assistant_text"] = assistant_preview

            if create_session:
                sessions = state.setdefault("sessions", [])
                existing = next(
                    (
                        item
                        for item in sessions
                        if item.get("session_id") == conversation_id
                    ),
                    None,
                )
                session_patch: dict[str, Any] = {
                    "session_id": conversation_id,
                    "type": "chat" if mode in {"auto", "chat"} else mode,
                    "status": "serving" if effective_status == "serving" else "idle",
                    "updated_at": _now(),
                }
                if user_preview or existing is None:
                    session_patch["title"] = (user_preview or assistant_preview or "闲聊")[:50]
                if existing is None:
                    session_patch["created_at"] = state.get("updated_at") or _now()
                _upsert_session(state, session_patch)

        state["updated_at"] = _now()
        _atomic_write(STATE_FILE, state)

    payload: dict[str, Any] = {
        "mode": mode,
        "status": effective_status,
        "provider": provider,
    }
    if user_preview:
        payload["user_text"] = user_preview
    if assistant_preview:
        payload["assistant_text"] = assistant_preview
    append_event("conversation.message", payload, conversation_id=conversation_id)


def start_chat(conversation_id: str, user_text: str, provider: str = "JoyInside") -> None:
    title = user_text[:40] or "闲聊"
    write_state_patch(
        {
            "active_conversation_id": conversation_id,
            "mode": "chat",
            "chat": {
                "provider": provider,
                "status": "serving",
                "last_user_text": user_text[:300],
            },
        }
    )
    with _locked():
        state = read_state()
        _upsert_session(
            state,
            {
                "session_id": conversation_id,
                "type": "chat",
                "title": title,
                "status": "serving",
                "created_at": state.get("updated_at") or _now(),
            },
        )
        state["updated_at"] = _now()
        _atomic_write(STATE_FILE, state)
    append_event(
        "chat.serving",
        {"provider": provider, "text": user_text[:300]},
        conversation_id=conversation_id,
    )


def finish_chat(
    conversation_id: str,
    assistant_text: str = "",
    status: str = "idle",
    provider: str = "JoyInside",
) -> None:
    write_state_patch(
        {
            "active_conversation_id": conversation_id,
            "mode": "chat",
            "chat": {
                "provider": provider,
                "status": status,
                "last_assistant_text": assistant_text[:500],
            },
        }
    )
    with _locked():
        state = read_state()
        _upsert_session(
            state,
            {
                "session_id": conversation_id,
                "type": "chat",
                "status": "idle" if status == "idle" else status,
            },
        )
        state["updated_at"] = _now()
        _atomic_write(STATE_FILE, state)
    append_event(
        "chat.finished",
        {"provider": provider, "status": status, "text": assistant_text[:500]},
        conversation_id=conversation_id,
    )


def set_proposal(
    *,
    conversation_id: str,
    state_name: str,
    function_name: str = "",
    task: str = "",
    proposal_text: str = "",
) -> None:
    task_id = f"task_{int(time.time())}" if state_name == "pending" else ""
    current = read_state()
    is_stale_completion = (
        state_name in {"accepted", "rejected", "completed"}
        and current.get("active_conversation_id")
        and current.get("active_conversation_id") != conversation_id
        and current.get("mode") == "chat"
    )
    patch: dict[str, Any] = {}
    if not is_stale_completion:
        patch.update(
            {
                "active_conversation_id": conversation_id,
                "mode": "task",
                "proposal": {
                    "state": state_name,
                    "function_name": function_name or "",
                    "task": task or "",
                    "proposal_text": proposal_text or "",
                },
            }
        )
    if task_id:
        patch["active_task_id"] = task_id
    if patch:
        write_state_patch(patch)
    with _locked():
        state = read_state()
        if task_id:
            _upsert_session(
                state,
                {
                    "session_id": task_id,
                    "type": "task",
                    "title": task[:50] or function_name or "任务",
                    "status": "pending",
                    "created_at": state.get("updated_at") or _now(),
                },
            )
        elif state.get("active_task_id") and state_name in {"accepted", "rejected", "completed"}:
            session_status = {
                "accepted": "running",
                "rejected": "rejected",
                "completed": "success",
            }.get(state_name, state_name)
            if state_name == "completed":
                active_task_id = state.get("active_task_id")
                task_workers = [
                    worker
                    for worker in state.get("workers", [])
                    if worker.get("task_id") in ("", None, active_task_id)
                ]
                if any(worker.get("status") == "failed" for worker in task_workers):
                    session_status = "failed"
                elif any(worker.get("status") == "running" for worker in task_workers):
                    session_status = "running"
            _upsert_session(
                state,
                {
                    "session_id": state.get("active_task_id"),
                    "type": "task",
                    "status": session_status,
                },
            )
        state["updated_at"] = _now()
        _atomic_write(STATE_FILE, state)
    append_event(
        f"proposal.{state_name}",
        {
            "function_name": function_name,
            "task": task,
            "proposal_text": proposal_text,
        },
        conversation_id=conversation_id,
        task_id=task_id or None,
    )


def start_worker(
    *,
    kind: str,
    task: str,
    run_id: str,
    worker_id: str | None = None,
    display_name: str | None = None,
    agent_id: str | None = None,
    workspace: str | None = None,
) -> None:
    worker_id = worker_id or f"{kind}_{agent_id or 'main'}"
    current_state = read_state()
    current_task_id = current_state.get("active_task_id") or ""
    proposal_state = (current_state.get("proposal") or {}).get("state")
    has_active_worker = any(
        worker.get("status") in {"pending", "accepted", "running"}
        for worker in current_state.get("workers", [])
    )
    active_task_id = (
        current_task_id
        if current_task_id and (proposal_state in {"pending", "accepted"} or has_active_worker)
        else run_id
    )
    worker = {
        "worker_id": worker_id,
        "kind": kind,
        "display_name": display_name or kind,
        "agent_id": agent_id or "",
        "status": "running",
        "task": task[:500],
        "task_id": active_task_id,
        "run_id": run_id,
        "started_at": _now(),
        "finished_at": None,
        "last_message": "running",
        "result_preview": "",
    }
    if workspace:
        worker["workspace"] = workspace

    with _locked():
        state = read_state()
        state["mode"] = "task"
        state["active_task_id"] = active_task_id
        _upsert_worker(state, worker)
        _upsert_session(
            state,
            {
                "session_id": active_task_id,
                "type": "task",
                "title": task[:50] or display_name or kind,
                "status": "running",
                "created_at": worker["started_at"],
            },
        )
        state["updated_at"] = _now()
        _atomic_write(STATE_FILE, state)
    append_event(
        "worker.running",
        worker,
        task_id=active_task_id,
    )


def finish_worker(
    *,
    run_id: str,
    status: str,
    result: str = "",
    worker_id: str | None = None,
) -> None:
    active_task_id = read_state().get("active_task_id") or run_id
    result_preview = (result or "")[:500]
    with _locked():
        state = read_state()
        workers = state.setdefault("workers", [])
        target_idx = None
        for idx, worker in enumerate(workers):
            if worker.get("run_id") == run_id or (
                worker_id and worker.get("worker_id") == worker_id
            ):
                target_idx = idx
                break
        if target_idx is not None:
            workers[target_idx].update(
                {
                    "status": status,
                    "finished_at": _now(),
                    "last_message": status,
                    "result_preview": result_preview,
                }
            )
            worker_payload = dict(workers[target_idx])
        else:
            worker_payload = {
                "worker_id": worker_id or run_id,
                "kind": "unknown",
                "display_name": worker_id or run_id,
                "status": status,
                "run_id": run_id,
                "finished_at": _now(),
                "last_message": status,
                "result_preview": result_preview,
            }
            workers.append(worker_payload)
        if active_task_id:
            _upsert_session(
                state,
                {
                    "session_id": active_task_id,
                    "type": "task",
                    "status": "success" if status == "success" else status,
                },
            )
        state["updated_at"] = _now()
        _atomic_write(STATE_FILE, state)
    append_event(
        f"worker.{status}",
        worker_payload,
        task_id=active_task_id,
    )


def reset_state() -> None:
    with _locked():
        _atomic_write(STATE_FILE, _default_state())
        EVENTS_FILE.write_text("", encoding="utf-8")
        for item in SESSIONS_DIR.glob("*.json"):
            item.unlink(missing_ok=True)
