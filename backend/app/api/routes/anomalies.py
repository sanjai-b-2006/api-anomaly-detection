from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.schemas.anomaly import DetectedAnomalyResponse
from app.models.anomaly import DetectedAnomaly
from app.api.deps import get_db

router = APIRouter()

@router.get("/", response_model=List[DetectedAnomalyResponse])
async def list_anomalies(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    resolved: bool = None
):
    query = select(DetectedAnomaly).order_by(DetectedAnomaly.timestamp.desc())
    if resolved is not None:
        query = query.where(DetectedAnomaly.resolved == resolved)
        
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    
    anomalies = result.scalars().all()
    return [DetectedAnomalyResponse.model_validate(a) for a in anomalies]
