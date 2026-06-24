from fastapi import APIRouter
from app.api.routes import metrics, anomalies, ws

api_router = APIRouter()
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(anomalies.router, prefix="/anomalies", tags=["anomalies"])
# WebSocket router is usually mounted directly without api prefix, but we can put it here
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
