import sys
import asyncio
from typing import Optional

from loguru import logger


class CentralizedLogger:
    def __init__(self, log_to_console: bool = True, log_file: Optional[str] = None):
        logger.remove()  # Remove any existing handlers
        
        if log_to_console:
            logger.add(sys.stdout, level="DEBUG")  # Console logging at INFO level
        if log_file is not None:
            logger.add(log_file, rotation="10 MB", retention="10 days", level="INFO")  # File logging with rotation

    async def shutdown(self):
        await asyncio.sleep(0)  # Placeholder for async compatibility if needed
        logger.info("Logger shutdown complete.")
