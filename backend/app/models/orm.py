import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite does not store tz info)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    prompt: Mapped[str] = mapped_column(Text, default="")
    provider_settings: Mapped[dict] = mapped_column(JSON, default=dict)  # never contains secrets
    story_request: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    story: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)    # StoryPlan without scenes
    scenes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)   # list of Scene dicts
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    jobs = relationship("JobRow", back_populates="project", cascade="all, delete-orphan", passive_deletes=True)
    character_links = relationship("ProjectCharacterRow", back_populates="project",
                                   cascade="all, delete-orphan", passive_deletes=True)


class CharacterRow(Base):
    __tablename__ = "characters"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    appearance: Mapped[str] = mapped_column(Text)
    personality: Mapped[str] = mapped_column(Text, default="")
    voice_preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    reference_image_paths: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    project_links = relationship("ProjectCharacterRow", back_populates="character",
                                 cascade="all, delete-orphan", passive_deletes=True)


class ProjectCharacterRow(Base):
    """Selection of a character in a project. Doubles as the appearance history."""
    __tablename__ = "project_characters"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(80), default="")
    selected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project = relationship("ProjectRow", back_populates="character_links")
    character = relationship("CharacterRow", back_populates="project_links")


class JobRow(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    stage: Mapped[str] = mapped_column(String(60), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    progress_kind: Mapped[str] = mapped_column(String(20), default="stage_based")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_files: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    project = relationship("ProjectRow", back_populates="jobs")
