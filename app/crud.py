"""
app/crud.py — database operations for alerts
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AlertModel, AlertCreate, AlertSeverity


async def create_alert(db: AsyncSession, data: AlertCreate) -> AlertModel:
    alert = AlertModel(
        id=str(uuid.uuid4()),
        title=data.title,
        message=data.message,
        severity=data.severity.value,
        source=data.source,
        resolved=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def get_alert(db: AsyncSession, alert_id: str) -> Optional[AlertModel]:
    result = await db.execute(select(AlertModel).where(AlertModel.id == alert_id))
    return result.scalar_one_or_none()


async def list_alerts(
    db: AsyncSession,
    severity: Optional[AlertSeverity] = None,
    resolved: Optional[bool] = None,
) -> list[AlertModel]:
    query = select(AlertModel).order_by(AlertModel.created_at.desc())
    if severity is not None:
        query = query.where(AlertModel.severity == severity.value)
    if resolved is not None:
        query = query.where(AlertModel.resolved == resolved)
    result = await db.execute(query)
    return list(result.scalars().all())


async def resolve_alert(db: AsyncSession, alert_id: str) -> Optional[AlertModel]:
    alert = await get_alert(db, alert_id)
    if not alert:
        return None
    alert.resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert


async def delete_alert(db: AsyncSession, alert_id: str) -> bool:
    alert = await get_alert(db, alert_id)
    if not alert:
        return False
    await db.delete(alert)
    await db.commit()
    return True
