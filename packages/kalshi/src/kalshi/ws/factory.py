import websockets
from typing import Dict, Optional


async def websocket_factory(uri: str, extra_headers: Optional[Dict[str, str]]):
    """Factory function that creates new websocket connections."""
    try:
        websocket = await websockets.connect(uri, extra_headers=extra_headers)
        print(f"connected to ws at {uri}")
        return websocket
    except Exception as e:
        print(f"failed to connect to websocket at {uri} with {e}")
        raise
