from fastapi import FastAPI
from app.api.router import router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "message":"Welcome to XingZhi Backend"
    }