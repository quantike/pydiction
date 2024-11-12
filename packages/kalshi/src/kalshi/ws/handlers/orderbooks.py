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
                    # Our orderbook takes the "YES" perspective on the market. This means we interpret the "NO"
                    # best bid as the best ask for "YES". This is done by taking 100 - yes_bid_price.
                    bids = [Level(level[0], level[1]) for level in data["yes"]]
                    asks = [Level(100-level[0], level[1]) for level in data["no"]]

                    # Build whole new book in the event that the current orderbook is empty
                    self.orderbook = Orderbook(bids=bids, asks=asks)

                    # Log the successful processing of the snapshot
                    logger.info(
                        f"Orderbook created: {self.orderbook.bba} mid {self.orderbook.mid_price} micro {self.orderbook.micro_price} spread {self.orderbook.spread},"
                    )

                case "orderbook_delta":
                    if data["side"] == "yes":
                        delta = Delta(price=data["price"], delta=data["delta"])
                        self.orderbook.update(self.orderbook.bids, delta)
                        logger.info(
                            f"Orderbook YES update: {self.orderbook.bba} mid {self.orderbook.mid_price} micro {self.orderbook.micro_price} spread {self.orderbook.spread}"
                        )

                    elif data["side"] == "no":
                        # Take the "YES" perspective and create the synthetic "YES" ask of 100-no_price
                        delta = Delta(price=100-data["price"], delta=data["delta"])
                        self.orderbook.update(self.orderbook.asks, delta)
                        logger.info(
                            f"Orderbook NO update: {self.orderbook.bba} mid {self.orderbook.mid_price} micro {self.orderbook.micro_price} spread {self.orderbook.spread}"
                        )

        except Exception as e:
            raise Exception(f"Tick process error: {e}")
