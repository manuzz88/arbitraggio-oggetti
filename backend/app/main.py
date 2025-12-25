from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.config import settings
from app.database import init_db
from app.api import items, listings, orders, analytics, scraper, images
from app.api import scheduler as scheduler_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Arbitraggio API...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Sistema di arbitraggio automatizzato per marketplace second-hand",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router, prefix=f"{settings.API_V1_PREFIX}/items", tags=["Items"])
app.include_router(listings.router, prefix=f"{settings.API_V1_PREFIX}/listings", tags=["Listings"])
app.include_router(orders.router, prefix=f"{settings.API_V1_PREFIX}/orders", tags=["Orders"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["Analytics"])
app.include_router(scraper.router, prefix=f"{settings.API_V1_PREFIX}/scraper", tags=["Scraper"])
app.include_router(scheduler_api.router, prefix=f"{settings.API_V1_PREFIX}/scheduler", tags=["Scheduler"])
app.include_router(images.router, prefix=f"{settings.API_V1_PREFIX}/images", tags=["Images"])


@app.get("/")
async def root():
    return {"message": "Arbitraggio API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
