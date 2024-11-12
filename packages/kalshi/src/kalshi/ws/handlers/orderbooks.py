from loguru import logger
from typing import Any, Dict

from common.models.orderbook import Orderbook
from common.models.level import Level
from common.models.delta import Delta


class KalshiOrderbookHandler:
    def __init__(self, orderbook: Orderbook) -> None:
        self.orderbook = orderbook

    def process(self, update_type: str, data: Dict[str, Any]) -> None:
        """
        Attempts to update the orderbook based on a data message. Parses 'orderbook_snapshot' via `refresh` and 'orderbook_delta' via `update.
        Will default to previous state if message fields cannot be parsed.

        Attributes:
            data(dict): A dictionary that represents the data from a `trade` message.
        """
        try:
            match update_type:
                case "orderbook_snapshot":
                    bids = [Level(level[0], level[1]) for level in data["yes"]]
                    asks = [Level(level[0], level[1]) for level in data["no"]]

                    # Build whole new book in the event that the current orderbook is empty
                    self.orderbook = Orderbook(bids=bids, asks=asks)

                    # Log the successful processing of the snapshot
                    logger.info(
                        f"Orderbook created: f{self.orderbook.bba} mid {self.orderbook.mid_price} micro {self.orderbook.micro_price} spread {self.orderbook.spread},"
                    )

                case "orderbook_delta":
                    delta = Delta(price=data["price"], delta=data["delta"])

                    if data["side"] == "yes":
                        self.orderbook.update(self.orderbook.bids, delta)
                        logger.info(f"Orderbook YES update: f{self.orderbook.bba}")

                    elif data["side"] == "no":
                        self.orderbook.update(self.orderbook.asks, delta)
                        logger.info(f"Orderbook NO update: f{self.orderbook.bba}")

        except Exception as e:
            raise Exception(f"Tick process error: {e}")
