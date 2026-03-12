import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers import ingestor, research, recommendation, health

app = FastAPI(
    title="Intelli-Credit API",
    description="AI-Powered Corporate Credit Appraisal Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(ingestor.router, prefix="/api/ingestor", tags=["Data Ingestor"])
app.include_router(research.router, prefix="/api/research", tags=["Research Agent"])
app.include_router(recommendation.router, prefix="/api/recommendation", tags=["Recommendation Engine"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
