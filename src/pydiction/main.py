import asyncio

from kalshi.models.status import KalshiStatus
from loguru import logger

from common.state import State
from kalshi.rest import KalshiRestClient
from kalshi.ws.client import KalshiWsClient
from common.clog import CentralizedLogger


async def main():
    state = None
    CentralizedLogger()

    try:
        state = State()

        api = KalshiRestClient(state)

        kalshi_status_checker = KalshiStatus.from_api(rest_client=api)

        websocket = KalshiWsClient(state)

        await websocket.connect()
        await websocket.add_subscription(
            ["ticker", "trade", "orderbook_delta", "market_lifecycle"]
        )

        await asyncio.gather(state.refresh(), websocket.monitor_connection_health(), kalshi_status_checker.run())

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.critical("pydiction manually cancelled by user")

    except Exception as e:
        logger.critical(f"pydiction encountered and unexpected error: {e}")
        raise

    finally:
        logger.info("pydiction successfully shutdown")


if __name__ == "__main__":
    asyncio.run(main())
