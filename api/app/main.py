from fastapi import FastAPI
from .db import Base, engine
from .routes import router

app = FastAPI(title="portfolio-pulse API")
Base.metadata.create_all(bind=engine)

app.include_router(router)
