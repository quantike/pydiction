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
    CentralizedLogger(log_file="pydiction.log")

    try:
        state = State()

        api = KalshiRestClient(state)

        kalshi_status_checker = KalshiStatus.from_api(rest_client=api)

        websocket = KalshiWsClient(state)

        await websocket.connect()
        await websocket.add_subscription(
            ["ticker", "trade", "orderbook_delta", "market_lifecycle"]
        )

        await asyncio.gather(
            state.refresh(),
            websocket.monitor_connection_health(),
            kalshi_status_checker.run(),
        )

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.critical("pydiction manually cancelled by user")

    except Exception as e:
        logger.critical(f"pydiction encountered and unexpected error: {e}")
        raise

    finally:
        # TODO: Documenting that we have an unbound error for the processes that we are initializing within the try statement.
        # Right now, they shouldn't be constructed outside of the try statement, but we may want to do this. We need to be able
        # to call the `.shutdown()` function for all of these processes in order to close the program successfully.
        logger.info("pydiction successfully shutdown")


if __name__ == "__main__":
    asyncio.run(main())
