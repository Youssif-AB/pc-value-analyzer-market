from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from backend.app.config import get_settings
from backend.app.constants import API_PREFIX, MODEL_CONTRACT_VERSION
from backend.app.db import Base, engine
from backend.app.routers import corrections, extraction, health, market, prediction


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()
app = FastAPI(
    title="PC Specs / Value Analyzer API",
    version=MODEL_CONTRACT_VERSION,
    description="Extract reviewable PC specs and estimate fair market value.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(extraction.router, prefix=API_PREFIX)
app.include_router(prediction.router, prefix=API_PREFIX)
app.include_router(corrections.router, prefix=API_PREFIX)
app.include_router(market.router, prefix=API_PREFIX)
app.mount("/metrics", make_asgi_app())
