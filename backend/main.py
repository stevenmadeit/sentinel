from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db, init_db
from .models import Commit, Incident

app = FastAPI(title="Sentinel API", version="1.0.0")

init_db()

RUNBOOKS_DIR = Path(__file__).resolve().parent.parent / "runbooks"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")


class AlertRequest(BaseModel):
    service_name: str
    alert_message: str


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "sentinel"}


@app.post("/alert", response_model=dict[str, Any])
def create_alert(payload: AlertRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not payload.service_name or not payload.alert_message:
        raise HTTPException(status_code=400, detail="service_name and alert_message are required")

    incident = Incident(
        service_name=payload.service_name,
        alert_message=payload.alert_message,
        status="open",
        created_at=datetime.now(timezone.utc),
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    try:
        likely_commit = _find_likely_commit(db, payload.service_name, incident.created_at)
        runbook_content = _load_relevant_runbook(payload.alert_message)
        ai_summary = _generate_ai_investigation(
            payload.alert_message,
            likely_commit,
            runbook_content,
        )

        incident.ai_summary = ai_summary
        incident.likely_commit = _format_commit_label(likely_commit)
        db.commit()
    except Exception as exc:  # pragma: no cover - defensive fallback
        incident.ai_summary = None
        incident.likely_commit = _format_commit_label(_find_likely_commit(db, payload.service_name, incident.created_at))
        incident.postmortem = f"AI analysis failed: {exc}"
        db.commit()

    return serialize_incident(incident)


@app.get("/incidents")
def list_incidents(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    incidents = db.query(Incident).order_by(Incident.created_at.desc()).all()
    return [serialize_incident(item) for item in incidents]


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return serialize_incident(incident)


@app.get("/commits")
def list_commits(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    commits = db.query(Commit).order_by(Commit.timestamp.desc()).all()
    return [serialize_commit(item) for item in commits]


def _find_likely_commit(db: Session, service_name: str, alert_time: datetime) -> Commit | None:
    return (
        db.query(Commit)
        .filter(Commit.service_name == service_name, Commit.timestamp <= alert_time)
        .order_by(Commit.timestamp.desc())
        .first()
    )


def _load_relevant_runbook(alert_message: str) -> str | None:
    if not RUNBOOKS_DIR.exists():
        return None

    tokens = [token for token in re.split(r"[^a-z0-9]+", alert_message.lower()) if token]
    if not tokens:
        return None

    best_match: tuple[int, str] | None = None
    for runbook_path in sorted(RUNBOOKS_DIR.glob("*.md")):
        content = runbook_path.read_text(encoding="utf-8")
        haystack = f"{runbook_path.stem} {content}".lower()
        score = sum(1 for token in tokens if token in haystack)
        if score > 0 and (best_match is None or score > best_match[0]):
            best_match = (score, content)

    return best_match[1] if best_match else None


def _generate_ai_investigation(alert_message: str, likely_commit: Commit | None, runbook_content: str | None) -> str:
    commit_context = (
        f"message: {likely_commit.message}; author: {likely_commit.author}"
        if likely_commit
        else "No matching commit found."
    )
    runbook_context = runbook_content or "No relevant runbook found."

    prompt = (
        "You are an incident investigation assistant for a service monitoring system. "
        "Given the alert message, the likely bad commit, and a relevant runbook, provide a concise analysis in this format:\n"
        "- likely root cause: ...\n"
        "- estimated user impact: ...\n"
        "- suggested fix: ...\n"
        f"Alert message: {alert_message}\n"
        f"Likely bad commit: {commit_context}\n"
        f"Runbook content:\n{runbook_context}"
    )

    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Ollama call failed: {exc}") from exc

    response_text = body.get("response", "").strip()
    if not response_text:
        raise RuntimeError("Ollama returned an empty response")

    return response_text


def _format_commit_label(commit: Commit | None) -> str | None:
    if not commit:
        return None
    label = f"{commit.message} — {commit.author}"
    return label if len(label) <= 100 else f"{label[:97]}..."


def serialize_incident(incident: Incident) -> dict[str, Any]:
    return {
        "id": incident.id,
        "service_name": incident.service_name,
        "alert_message": incident.alert_message,
        "status": incident.status,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
        "ai_summary": incident.ai_summary,
        "likely_commit": incident.likely_commit,
        "postmortem": incident.postmortem,
    }


def serialize_commit(commit: Commit) -> dict[str, Any]:
    return {
        "id": commit.id,
        "service_name": commit.service_name,
        "message": commit.message,
        "author": commit.author,
        "timestamp": commit.timestamp.isoformat() if commit.timestamp else None,
    }
