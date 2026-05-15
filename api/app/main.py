from fastapi import FastAPI

from .routes import router

app = FastAPI(title="Konto-Kompass API", version="0.2.0")
app.include_router(router)
