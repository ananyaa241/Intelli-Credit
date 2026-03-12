from fastapi import APIRouter
from pydantic import BaseModel
from config import GEMINI_API_KEY, SERPER_API_KEY

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    gemini_configured: bool
    serper_configured: bool
    version: str

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        gemini_configured=bool(GEMINI_API_KEY),
        serper_configured=bool(SERPER_API_KEY),
        version="1.0.0",
    )
