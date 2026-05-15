from pydantic import BaseModel
import os


class Settings(BaseModel):
    database_url: str = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://konto:konto@localhost:5432/konto_kompass",
    )
    app_secret: str = os.environ.get("APP_SECRET", "dev-change-me")
    app_env: str = os.environ.get("APP_ENV", "dev")
    jwt_expire_minutes: int = int(os.environ.get("JWT_EXPIRE_MINUTES", "10080"))
    jwt_algorithm: str = "HS256"


settings = Settings()
