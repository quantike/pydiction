from typing import Dict


class KalshiMessageHandler:
    def __init__(self) -> None:
        self.message_type_map = {
            "orderbook_snapshot": self._handle_snapshot_,
            "orderbook_delta": self._handle_delta_,
            "ticker": self._handle_ticker_,
            "trade": self._handle_trade_,
            "fill": self._handle_fill_,
            "market_lifecycle": self._handle_market_lifecycle_,
        }

    def handle_message(self, message: Dict) -> None:
        message_type: str = message.get("type", "")
        handler = self.message_type_map.get(message_type, self._handle_unexpected_)
        handler(message)

    def _handle_snapshot_(self, message: Dict) -> None:
        print(f"snapshot: {message}")
        pass

    def _handle_delta_(self, message: Dict) -> None:
        print(f"delta: {message}")
        pass

    def _handle_ticker_(self, message: Dict) -> None:
        print(f"ticker: {message}")
        pass

    def _handle_trade_(self, message: Dict) -> None:
        print(f"trade: {message}")
        pass

    def _handle_fill_(self, message: Dict) -> None:
        print(f"fill: {message}")
        pass

    def _handle_market_lifecycle_(self, message: Dict) -> None:
        print(f"lifecycle: {message}")
        pass

    def _handle_unexpected_(self, message: Dict) -> None:
        print(f"unexpected: {message}")
        pass
