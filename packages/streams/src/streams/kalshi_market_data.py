from typing import Coroutine
from common.state import State
from kalshi.authentication import Authenticator
from kalshi.ws.client import KalshiWsClient
from kalshi.ws.factory import websocket_factory


class KalshiMarketData:
    """
    Manages market data streams for Kalshi. Includes order book, best bid-ask, trades, and ticks.

    Attributes:
        state(State): An instance of the application state.
        ws_conn(KalshiWsClient): An instance of the KalshiWsClient connection.
    """

    def __init__(self, state: State) -> None:
        self.state = state
        self._auth_ = Authenticator(state)
        self.ws_conn = KalshiWsClient(state=state, auth=self._auth_, websocket_factory=websocket_factory)

    async def _stream_(self):
        pass

    async def start(self) -> Coroutine:
        await self._stream_()
