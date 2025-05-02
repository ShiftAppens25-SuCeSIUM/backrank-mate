import os


class Settings:
    APP_NAME: str = os.environ.get("APP_NAME", "My FastAPI App")
    DEBUG: bool = os.environ.get("DEBUG", "true").lower() == "true"


settings = Settings()
