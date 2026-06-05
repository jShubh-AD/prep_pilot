import logging
from app.storage.s3 import s3_service

logger = logging.getLogger(__name__)


async def initialize_services():
    try:
        logger.info("Initializing S3 service...")
        s3_service.initialize()
        s3_service.health_check()
        logger.info("All services initialized successfully")

    except Exception:
        logger.error("Application startup failed")
        raise