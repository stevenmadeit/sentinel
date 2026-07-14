from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.database import SessionLocal, init_db
from backend.models import Commit


def seed_data() -> None:
    init_db()
    db = SessionLocal()

    try:
        existing = db.query(Commit).count()
        if existing:
            print("Database already contains seed data.")
            return

        commits = [
            Commit(
                service_name="payments-service",
                message="Fix retry logic for stripe webhook retries",
                author="maya@company.com",
                timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            ),
            Commit(
                service_name="payments-service",
                message="Add idempotency key support for payment callbacks",
                author="jules@company.com",
                timestamp=datetime.now(timezone.utc) - timedelta(days=5),
            ),
            Commit(
                service_name="auth-service",
                message="Rotate signing keys for token validation",
                author="alex@company.com",
                timestamp=datetime.now(timezone.utc) - timedelta(days=6),
            ),
            Commit(
                service_name="auth-service",
                message="Reduce session cache TTL for stale login handling",
                author="nina@company.com",
                timestamp=datetime.now(timezone.utc) - timedelta(days=9),
            ),
            Commit(
                service_name="inventory-service",
                message="Patch timeout handling for warehouse sync",
                author="omar@company.com",
                timestamp=datetime.now(timezone.utc) - timedelta(days=12),
            ),
            Commit(
                service_name="inventory-service",
                message="Improve queue backoff for supplier reconciliation",
                author="sara@company.com",
                timestamp=datetime.now(timezone.utc) - timedelta(days=15),
            ),
        ]
        db.add_all(commits)
        db.commit()
        print("Seeded fake commit history.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
