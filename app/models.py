"""
app/models.py — ORM table definition + Pydantic request/response schemas
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ── Enum ──────────────────────────────────────────────────────────────────────

class AlertSeverity(str, Enum):
    info     = "info"
    warning  = "warning"
    critical = "critical"


# ── ORM model ─────────────────────────────────────────────────────────────────

class AlertModel(Base):
    __tablename__ = "alerts"

    id:          Mapped[str]           = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title:       Mapped[str]           = mapped_column(String(120), nullable=False)
    message:     Mapped[str]           = mapped_column(String(1000), nullable=False)
    severity:    Mapped[str]           = mapped_column(String(20), nullable=False, default="warning")
    source:      Mapped[str]           = mapped_column(String(120), nullable=False, default="manual")
    resolved:    Mapped[bool]          = mapped_column(Boolean, nullable=False, default=False)
    created_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False,
                                                        default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    title:    str           = Field(..., min_length=3, max_length=120, examples=["High CPU Usage"])
    message:  str           = Field(..., min_length=5, max_length=1000, examples=["CPU exceeded 90% for 5 minutes"])
    severity: AlertSeverity = AlertSeverity.warning
    source:   str           = Field(default="manual", examples=["sentinel-agent"])


class AlertRead(BaseModel):
    id:          str
    title:       str
    message:     str
    severity:    AlertSeverity
    source:      str
    resolved:    bool
    created_at:  datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    count:  int
    alerts: list[AlertRead]
