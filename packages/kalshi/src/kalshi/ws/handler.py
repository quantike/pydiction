from common.models.orderbook import Orderbook
from common.models.trade import Trade
from loguru import logger
from typing import Dict

from common.models.tick import Tick
from kalshi.models.lifecycle import Lifecycle
from kalshi.ws.handlers.lifecycles import KalshiLifecycleHandler
from kalshi.ws.handlers.orderbooks import KalshiOrderbookHandler
from kalshi.ws.handlers.ticks import KalshiTickHandler
from kalshi.ws.handlers.trades import KalshiTradeHandler


class KalshiMessageHandler:
    def __init__(self) -> None:
        self.message_type_map = {
            "orderbook_snapshot": self._handle_book_update_,
            "orderbook_delta": self._handle_book_update_,
            "ticker": self._handle_ticker_,
            "trade": self._handle_trade_,
            "fill": self._handle_fill_,
            "market_lifecycle": self._handle_market_lifecycle_,
        }
        self.tick = KalshiTickHandler(tick=Tick.empty())
        self.trade = KalshiTradeHandler(trade=Trade.empty())
        self.orderbook = KalshiOrderbookHandler(orderbook=Orderbook.empty())
        self.lifecycle = KalshiLifecycleHandler(lifecycle=Lifecycle.empty())

    def handle_message(self, message: Dict) -> None:
        message_type: str = message.get("type", "")
        handler = self.message_type_map.get(message_type, self._handle_unexpected_)
        handler(message)

    def _handle_book_update_(self, message: Dict) -> None:
        logger.debug(f"book: {message}")
        update_type: str = message.get("type", "")
        self.orderbook.process(update_type, message["msg"])

    def _handle_ticker_(self, message: Dict) -> None:
        logger.debug(f"ticker: {message}")
        self.tick.process(message["msg"])

    def _handle_trade_(self, message: Dict) -> None:
        logger.debug(f"trade: {message}")
        self.trade.process(message["msg"])

    def _handle_fill_(self, message: Dict) -> None:
        logger.debug(f"fill: {message}")
        pass

    def _handle_market_lifecycle_(self, message: Dict) -> None:
        logger.debug(f"lifecycle: {message}")
        self.lifecycle.process(message["msg"])

    def _handle_unexpected_(self, message: Dict) -> None:
        logger.error(f"unexpected: {message}")
        pass
