from typing import Dict, Optional

import websockets
from loguru import logger


async def websocket_factory(uri: str, extra_headers: Optional[Dict[str, str]]):
    """Factory function that creates new websocket connections."""
    try:
        websocket = await websockets.connect(uri, extra_headers=extra_headers)
        logger.debug(f"connected to ws at {uri}")
        return websocket
    except Exception as e:
        logger.error(f"failed to connect to websocket at {uri} with {e}")
        raise
