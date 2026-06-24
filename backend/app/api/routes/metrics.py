from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.schemas.metric import MetricDataPointCreate, MetricDataPointResponse
from app.api.deps import get_db
from app.services.metric_service import process_metric

router = APIRouter()

@router.post("/", response_model=Dict[str, str])
async def create_metric(
    metric_in: MetricDataPointCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest a new metric point via REST API.
    Processing happens in the background to ensure fast response.
    """
    # Run processing in background to not block the API
    background_tasks.add_task(process_metric, db, metric_in)
    return {"status": "accepted"}
