from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db, init_db
from .models import Commit, Incident

app = FastAPI(title="Sentinel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    likely_commit = _find_likely_commit(db, payload.service_name, incident.created_at)
    runbook_content = _load_relevant_runbook(payload.alert_message)

    try:
        ai_payload, ai_summary_text = _generate_ai_investigation(
            payload.alert_message,
            likely_commit,
            runbook_content,
        )
        incident.ai_summary = ai_summary_text
        incident.likely_commit = _format_commit_label(likely_commit)
        incident.slack_message = _format_slack_message(
            payload.service_name,
            payload.alert_message,
            ai_payload,
            likely_commit,
        )
        print(incident.slack_message)
        db.commit()
    except Exception as exc:  # pragma: no cover - defensive fallback
        incident.ai_summary = None
        incident.likely_commit = _format_commit_label(likely_commit)
        incident.slack_message = _format_slack_message(
            payload.service_name,
            payload.alert_message,
            {
                "cause": f"AI analysis failed: {exc}",
                "impact": "Unknown",
                "fix": "Investigate the incident manually and review recent commits.",
            },
            likely_commit,
        )
        incident.postmortem = f"AI analysis failed: {exc}"
        print(incident.slack_message)
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


@app.post("/incidents/{incident_id}/resolve", response_model=dict[str, Any])
def resolve_incident(incident_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.status == "resolved":
        raise HTTPException(status_code=400, detail="Incident is already resolved")

    incident.status = "resolved"
    incident.resolved_at = datetime.now(timezone.utc)

    likely_commit = _find_likely_commit(db, incident.service_name, incident.created_at)
    runbook_content = _load_relevant_runbook(incident.alert_message)

    try:
        incident.postmortem = _generate_postmortem(incident, likely_commit, runbook_content)
    except Exception as exc:  # pragma: no cover - best-effort fallback
        incident.postmortem = f"Postmortem generation failed: {exc}"

    db.commit()
    db.refresh(incident)
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


def _generate_ai_investigation(alert_message: str, likely_commit: Commit | None, runbook_content: str | None) -> tuple[dict[str, str], str]:
    commit_context = (
        f"message: {likely_commit.message}; author: {likely_commit.author}"
        if likely_commit
        else "No matching commit found."
    )
    runbook_context = runbook_content or "No relevant runbook found."

    prompt = (
        "You are an incident investigation assistant for a service monitoring system. "
        "Given the alert message, the likely bad commit, and a relevant runbook, return only a valid JSON object with these keys:\n"
        "  - cause\n"
        "  - impact\n"
        "  - fix\n"
        "Do not include any explanatory text outside the JSON object.\n"
        f"Alert message: {alert_message}\n"
        f"Likely bad commit: {commit_context}\n"
        f"Runbook content:\n{runbook_context}\n"
        "If you cannot generate valid JSON, still include the fields clearly labeled in plain text."
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

    parsed = _parse_ai_response(response_text)
    summary_text = (
        f"Likely cause: {parsed['cause']}\n"
        f"Estimated impact: {parsed['impact']}\n"
        f"Suggested fix: {parsed['fix']}"
    )
    return parsed, summary_text


def _parse_ai_response(response_text: str) -> dict[str, str]:
    def as_dict(parsed: Any) -> dict[str, str]:
        return {
            "cause": str(parsed.get("cause", "Unknown")).strip(),
            "impact": str(parsed.get("impact", "Unknown")).strip(),
            "fix": str(parsed.get("fix", "Unknown")).strip(),
        }

    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return as_dict(parsed)
    except json.JSONDecodeError:
        pass

    json_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, dict):
                return as_dict(parsed)
        except json.JSONDecodeError:
            pass

    result = {"cause": None, "impact": None, "fix": None}
    patterns = {
        "cause": r"(?:likely root cause|cause)[:\-]\s*(.+?)(?:\n|$)",
        "impact": r"(?:estimated user impact|impact)[:\-]\s*(.+?)(?:\n|$)",
        "fix": r"(?:suggested fix|fix)[:\-]\s*(.+?)(?:\n|$)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, cleaned, flags=re.IGNORECASE | re.DOTALL)
        if match:
            result[key] = match.group(1).strip()

    return {
        "cause": result["cause"] or cleaned.strip() or "Unknown",
        "impact": result["impact"] or "Unknown",
        "fix": result["fix"] or "Unknown",
    }


def _generate_postmortem(incident: Incident, likely_commit: Commit | None, runbook_content: str | None) -> str:
    commit_label = _format_commit_label(likely_commit) or incident.likely_commit or "No matching commit found"
    runbook_context = runbook_content or "No relevant runbook was matched."
    ai_summary = incident.ai_summary or "AI analysis was unavailable or failed."

    prompt = (
        "You are an incident postmortem writer. Write a markdown postmortem using the sections: Timeline, Root cause, Resolution, Prevention. "
        "Use the incident context below."
        "\n\nIncident context:\n"
        f"Alert message: {incident.alert_message}\n"
        f"Likely commit: {commit_label}\n"
        f"Runbook content:\n{runbook_context}\n"
        f"AI summary:\n{ai_summary}\n"
        f"Alert raised at: {incident.created_at.isoformat() if incident.created_at else 'unknown'}\n"
        f"Incident resolved at: {incident.resolved_at.isoformat() if incident.resolved_at else 'unknown'}\n"
        "Return only markdown text with headings for each section."
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
        raise RuntimeError(f"Ollama postmortem generation failed: {exc}") from exc

    postmortem = body.get("response", "").strip()
    if not postmortem:
        raise RuntimeError("Ollama returned an empty postmortem response")

    return postmortem


def _format_slack_message(
    service_name: str,
    alert_message: str,
    ai_payload: dict[str, str],
    likely_commit: Commit | None,
) -> str:
    commit_label = _format_commit_label(likely_commit) or "No matching commit found"
    return (
        f"🚨 Incident detected: {service_name}\n"
        f"Alert: {alert_message}\n"
        f"Likely cause: {ai_payload['cause']}\n"
        f"Estimated impact: {ai_payload['impact']}\n"
        f"Suggested fix: {ai_payload['fix']}\n"
        f"Likely commit: {commit_label}"
    )


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
        "slack_message": incident.slack_message,
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
