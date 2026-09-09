"""FastAPI Application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from financial_ai.api.routes import router

app = FastAPI(
    title="Financial AI Assistant API",
    description="End-to-End Financial Analysis AI Assistant utilizing RAG and Text-to-SQL on SEC EDGAR data for AAPL, MSFT, and NVDA.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "Financial AI Assistant API is running.",
        "docs_url": "/docs",
        "supported_companies": ["AAPL", "MSFT", "NVDA"],
    }
