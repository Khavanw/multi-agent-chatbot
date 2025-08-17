import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.startup import initialize_app_services_sync

from app.api.v1.router import api_router
from app.settings import APP_SETTINGS

logger = logging.getLogger(__name__)


app = FastAPI(
    title=APP_SETTINGS.APP_NAME,
    version=APP_SETTINGS.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


@app.on_event("startup")
async def startup_event():
    """FastAPI startup event"""
    try:
        logger.info("🚀 FastAPI startup event triggered")
        await initialize_app_services_sync()
        logger.info("✅ Startup completed successfully")
    except Exception as e:
        logger.error(f"❌ Startup event failed: {str(e)}")
        # Try sync initialization as fallback
        logger.info("🔄 Attempting sync fallback initialization...")
        initialize_app_services_sync()


# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """
    Root endpoint for health check.
    """
    return {"status": "ok", "message": f"Welcome to {APP_SETTINGS.APP_NAME} API"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
