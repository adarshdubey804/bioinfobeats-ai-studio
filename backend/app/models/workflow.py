import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, JSON, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
class Workflow(Base):
    __tablename__ = 'workflows'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default='draft', nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
