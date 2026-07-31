from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from .models import Base

DATABASE_URL = "sqlite:///./backend/sentinel.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "incidents" in inspector.get_table_names():
        columns = [column["name"] for column in inspector.get_columns("incidents")]
        if "slack_message" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE incidents ADD COLUMN slack_message TEXT"))
                conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
