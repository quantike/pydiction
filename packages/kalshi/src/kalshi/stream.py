from common.state import State

from kalshi.authentication import Authenticator
from kalshi.rest import KalshiRestClient
from kalshi.ws.client import KalshiWsClient


class KalshiStream:
    _channels_ = ["orderbook_delta", "ticker", "trade"]

    def __init__(self, state: State) -> None:
        self.state = state
        self.auth = Authenticator(self.state)
        self.rest_client = KalshiRestClient(self.state)
        self.ws_client = KalshiWsClient(self.state)

    async def _initialize_(self) -> None:
        # Check REST client
        if not self.rest_client.is_connected:
            raise ConnectionError("Unable to connect to Kalshi REST Client")

        # Set up WebSocket Client
        await self.ws_client.start()
        await self.ws_client.add_subscription(self._channels_)

    async def _stream_(self):
        pass


class MarketDataFeeds:
    def __init__(self, state: State, auth: Authenticator) -> None:
        self.state = state
        self.auth = auth

    async def start(self) -> None:
        """
        Starts the WebSocket data feeds.
        """
        # tasks = []
        ...
