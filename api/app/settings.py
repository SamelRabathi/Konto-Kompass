from pydantic import BaseModel
import os

class Settings(BaseModel):
    database_url: str = os.environ["DATABASE_URL"]
    app_secret: str = os.environ.get("APP_SECRET", "dev")
    app_env: str = os.environ.get("APP_ENV", "dev")

settings = Settings()
