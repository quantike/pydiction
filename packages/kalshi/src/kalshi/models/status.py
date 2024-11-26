import asyncio

from typing import Dict
from loguru import logger
from kalshi.rest import KalshiRestClient


class KalshiStatus:
    def __init__(
        self, rest_client: KalshiRestClient, polling_interval: int = 60
    ) -> None:
        self._exchange_active: bool = False
        self._trading_active: bool = False
        self.rest_client = rest_client
        self.polling_interval = polling_interval
        self._running = False

    @staticmethod
    def from_api(
        rest_client: KalshiRestClient, polling_interval: int = 60
    ) -> "KalshiStatus":
        instance = KalshiStatus(rest_client, polling_interval)
        try:
            status_response = rest_client.get_exchange_status()
            instance._exchange_active = status_response.get("exchange_active", False)
            instance._trading_active = status_response.get("trading_active", False)
        except Exception as e:
            logger.error(f"Failed to fetch initial status: {e}")
            raise

        logger.info(f"Kalshi status {instance.status}")
        return instance

    @property
    def status(self) -> str:
        match self._exchange_active, self._trading_active:
            case True, True:
                return "ACTIVE_TRADING_ENABLED"
            case True, False:
                return "ACTIVE_TRADING_DISABLED"
            case False, True:
                return "INVALID_STATE"
            case False, False:
                return "INACTIVE_TRADING_DISABLED"

    @property
    def is_trading_active(self) -> bool:
        return self.status == "ACTIVE_TRADING_ENABLED"

    def _update_status_(self, new_status: Dict[str, bool]) -> None:
        exchange_active = new_status.get("exchange_active", self._exchange_active)
        trading_active = new_status.get("trading_active", self._trading_active)

        if (exchange_active, trading_active) != (
            self._exchange_active,
            self._trading_active,
        ):
            old_state = self.status
            self._exchange_active = exchange_active
            self._trading_active = trading_active
            logger.info(f"Exchange status changed from {old_state} to {self.status}")

    async def _poll_status_(self):
        """Poll the exchange status at regular intervals and update the state."""
        while self._running:
            try:
                response = self.rest_client.get_exchange_status()
                self._update_status_(response)
                await asyncio.sleep(self.polling_interval)
            except Exception as e:
                logger.error(f"Error polling exchange status: {e}")
                await asyncio.sleep(self.polling_interval)

    async def run(self):
        """Start the status polling loop."""
        self._running = True
        await self._poll_status_()

    def shutdown(self):
        """Stop the status polling loop."""
        self._running = False
