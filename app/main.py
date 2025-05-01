from fastapi import FastAPI
from app.routes import hello
from config.config import settings

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.include_router(hello.router)

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}!"}
