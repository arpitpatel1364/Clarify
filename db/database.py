"""
Clarify — Database Layer
SQLAlchemy models + session management
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    create_engine, Column, String, Text, Boolean,
    Integer, Float, DateTime, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from config.settings import DB_PATH


class Base(DeclarativeBase):
    pass


class SessionRecord(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    os = Column(String, default="linux")
    provider = Column(String)

    explanations = relationship("Explanation", back_populates="session", cascade="all, delete-orphan")


class Explanation(Base):
    __tablename__ = "explanations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"))
    selected_text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    source_app = Column(String)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    tokens_used = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_bookmarked = Column(Boolean, default=False)
    user_rating = Column(Integer)

    session = relationship("SessionRecord", back_populates="explanations")
    messages = relationship("Message", back_populates="explanation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    explanation_id = Column(String, ForeignKey("explanations.id"))
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    explanation = relationship("Explanation", back_populates="messages")


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String, unique=True, nullable=False)
    api_key = Column(Text)
    base_url = Column(String)
    model = Column(String)
    is_active = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# ── Engine & Session ──────────────────────────────────────────────────────────

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Session:
    return SessionLocal()


def get_or_create_provider(db: Session, provider: str) -> ProviderConfig:
    cfg = db.query(ProviderConfig).filter_by(provider=provider).first()
    if not cfg:
        defaults = {
            "claude":  {"model": "claude-sonnet-4-20250514", "base_url": ""},
            "openai":  {"model": "gpt-4o",                  "base_url": ""},
            "gemini":  {"model": "gemini-1.5-flash",         "base_url": ""},
            "groq":    {"model": "llama3-70b-8192",          "base_url": ""},
            "ollama":  {"model": "llama3",                   "base_url": "http://localhost:11434"},
            "openrouter": {"model": "openai/gpt-4o",         "base_url": "https://openrouter.ai/api/v1"},
        }
        d = defaults.get(provider, {"model": "default", "base_url": ""})
        cfg = ProviderConfig(provider=provider, model=d["model"], base_url=d["base_url"])
        db.add(cfg)
        db.commit()
    return cfg


def save_explanation(
    db: Session,
    session_id: str,
    selected_text: str,
    explanation_text: str,
    provider: str,
    model: str,
    source_app: str = "",
    tokens: int = 0,
) -> Explanation:
    exp = Explanation(
        session_id=session_id,
        selected_text=selected_text,
        explanation=explanation_text,
        provider=provider,
        model=model,
        source_app=source_app,
        tokens_used=tokens,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


def save_message(db: Session, explanation_id: str, role: str, content: str) -> Message:
    msg = Message(explanation_id=explanation_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_history(db: Session, limit: int = 100) -> List[Explanation]:
    return (
        db.query(Explanation)
        .order_by(Explanation.created_at.desc())
        .limit(limit)
        .all()
    )


def toggle_bookmark(db: Session, explanation_id: str) -> bool:
    exp = db.query(Explanation).filter_by(id=explanation_id).first()
    if exp:
        exp.is_bookmarked = not exp.is_bookmarked
        db.commit()
        return exp.is_bookmarked
    return False
