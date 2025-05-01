from fastapi import FastAPI
from app.routes import fact_checker
from config.config import settings
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.include_router(fact_checker.router)

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}!"}
