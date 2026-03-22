"""
Sentinel API — Server Health Monitor
Real-time system metrics + persistent alert management.
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, metrics
from app.auth import require_api_key
from app.database import get_db, init_db
from app.models import AlertCreate, AlertListResponse, AlertRead, AlertSeverity


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()          # create tables if they don't exist
    yield
    # nothing to tear down for SQLite


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Sentinel API",
    description=(
        "Real-time server health monitoring and persistent alert management. "
        "Part of the [Sentinel](https://github.com/AlbertNjobo/sentinel) project."
    ),
    version="1.0.0",
    lifespan=lifespan,
    contact={"name": "Lawrence", "url": "https://github.com/AlbertNjobo"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"], summary="API info")
def root():
    return {
        "name": "Sentinel API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "operational",
        "endpoints": {
            "health":    "/health",
            "metrics":   "/metrics",
            "processes": "/processes",
            "alerts":    "/alerts",
        },
    }


# ── Health ────────────────────────────────────────────────────────────────────

@app.get(
    "/health",
    tags=["Monitoring"],
    summary="Liveness probe",
    description="Quick health check — used by load balancers and uptime monitors.",
)
def health_check():
    return metrics.health_snapshot()


# ── Metrics ───────────────────────────────────────────────────────────────────

@app.get(
    "/metrics",
    tags=["Monitoring"],
    summary="Full system metrics",
    description="CPU, memory, disk, network, and host info.",
)
def get_metrics():
    return metrics.full_metrics()


@app.get(
    "/processes",
    tags=["Monitoring"],
    summary="Top processes by CPU",
)
def get_processes(
    limit: int = Query(default=10, ge=1, le=50, description="Number of processes to return"),
):
    return metrics.top_processes(limit)


# ── Alerts ────────────────────────────────────────────────────────────────────

@app.get(
    "/alerts",
    response_model=AlertListResponse,
    tags=["Alerts"],
    summary="List all alerts",
)
async def list_alerts(
    severity: Optional[AlertSeverity] = Query(default=None, description="Filter by severity"),
    resolved: Optional[bool]          = Query(default=None, description="Filter by resolved status"),
    db: AsyncSession = Depends(get_db),
):
    alerts = await crud.list_alerts(db, severity=severity, resolved=resolved)
    return AlertListResponse(count=len(alerts), alerts=alerts)


@app.post(
    "/alerts",
    response_model=AlertRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Alerts"],
    summary="Create a new alert",
)
async def create_alert(
    body: AlertCreate,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    return await crud.create_alert(db, body)


@app.get(
    "/alerts/{alert_id}",
    response_model=AlertRead,
    tags=["Alerts"],
    summary="Get a single alert",
)
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    alert = await crud.get_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@app.patch(
    "/alerts/{alert_id}/resolve",
    response_model=AlertRead,
    tags=["Alerts"],
    summary="Resolve an alert",
)
async def resolve_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    alert = await crud.resolve_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@app.delete(
    "/alerts/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Alerts"],
    summary="Delete an alert",
)
async def delete_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    deleted = await crud.delete_alert(db, alert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found")
