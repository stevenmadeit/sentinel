from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db, init_db
from .models import Commit, Incident

app = FastAPI(title="Sentinel API", version="1.0.0")

init_db()


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
