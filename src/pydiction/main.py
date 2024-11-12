import asyncio

from loguru import logger

from common.state import State
from kalshi.ws.client import KalshiWsClient


async def main():
    state = None

    try:
        state = State()
        websocket = KalshiWsClient(state)
        await websocket.connect()
        await websocket.add_subscription(["ticker", "trade", "orderbook_delta"])

        await asyncio.gather(state.refresh(), websocket.monitor_connection_health())

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.critical("pydiction manually cancelled by user")

    except Exception as e:
        logger.critical(f"pydiction encountered and unexpected error: {e}")
        raise

    finally:
        logger.info("pydiction successfully shutdown")


if __name__ == "__main__":
    asyncio.run(main())
