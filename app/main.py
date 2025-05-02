"""
This is the main entry point for the FastAPI application.
It initializes the FastAPI app, loads environment variables,
and includes the necessary routes.
It also sets up the application with the title and debug mode
based on the configuration settings.
The application is designed to be run with Uvicorn or another ASGI server.
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.routes import fact_checker
from config.config import settings

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.include_router(fact_checker.router)


@app.get("/")
def read_root():
    """Root endpoint that returns a welcome message."""
    return {"message": f"Welcome to {settings.APP_NAME}!"}
