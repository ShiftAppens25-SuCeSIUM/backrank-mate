"""Settings module for the application."""
import os


class Settings:
    """Settings for the application.
    This class loads environment variables and provides default values for the application settings.
    """

    APP_NAME: str = os.environ.get("APP_NAME", "My FastAPI App")
    DEBUG: bool = os.environ.get("DEBUG", "true").lower() == "true"


settings = Settings()
