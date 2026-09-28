import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from loguru import logger
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.db import Base, engine
from app.exceptions import DiagnosticAppException, app_exception_handler
from app.limiter import limiter
from app.routers import auth, diagnostics, bookings, payments

# Configure structured logging globally
logger.remove()
logger.add(sys.stdout, serialize=True, level="INFO")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema
    Base.metadata.create_all(bind=engine)
    
    # Initialize Cache
    try:
        redis = aioredis.from_url("redis://redis:6379", encoding="utf8", decode_responses=True)
        await redis.ping()
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
        logger.info("FastAPI cache successfully initialized with Redis backend.")
    except Exception as e:
        logger.warning(f"Could not connect to Redis, falling back to InMemoryBackend: {e}")
        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
        
    yield
    logger.info("Application shutdown.")


app = FastAPI(
    title="Diagnostic Booking Service", 
    version="1.0.0",
    description="A robust API for booking diagnostic tests and simulating payments.",
    lifespan=lifespan
)

# Apply Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Custom Error Handling
app.add_exception_handler(DiagnosticAppException, app_exception_handler)

# Include API Routers
app.include_router(auth.router)
app.include_router(diagnostics.router)
app.include_router(bookings.router)
app.include_router(payments.router)

@app.get("/health", tags=["Health"], summary="Health Check")
@limiter.limit("10/minute")
def health_check(request: Request):
    """Provides a quick health check endpoint to verify the service is running."""
    return {"status": "ok", "message": "Service is up and running securely!"}
