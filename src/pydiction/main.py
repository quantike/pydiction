import asyncio

from common.clog import CentralizedLogger
from common.state import State
from kalshi.models.status import KalshiStatus
from kalshi.rest import KalshiRestClient
from kalshi.ws.client import KalshiWsClient
from loguru import logger

async def main():
    state = None
    kalshi_status_checker: KalshiStatus | None = None
    websocket: KalshiWsClient | None = None
    CentralizedLogger(log_file="pydiction.log")

    try:
        state = State()

        api = KalshiRestClient(state)

        kalshi_status_checker = KalshiStatus.from_api(rest_client=api)

        websocket = KalshiWsClient(state)
        await websocket.start()
        await websocket.add_subscription(
            ["ticker", "trade", "orderbook_delta", "market_lifecycle"]
        )

        await asyncio.gather(
            state.refresh(),
            kalshi_status_checker.run(),
        )

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.critical("pydiction manually cancelled by user")

    except Exception as e:
        logger.critical(f"pydiction encountered an unexpected error: {e}")
        raise

    finally:
        if websocket:
            await websocket.end()
        logger.success("pydiction successfully shutdown")

if __name__ == "__main__":
    asyncio.run(main())
