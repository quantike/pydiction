from typing import Any, Dict

from common.models.delta import Delta
from common.models.level import Level
from common.models.orderbook import Orderbook
from loguru import logger


class KalshiOrderbookHandler:
    def __init__(self, orderbook: Orderbook) -> None:
        self.orderbook = orderbook

    def process(self, data: Dict[str, Any]) -> None:
        """
        Attempts to update the orderbook based on a data message. Parses 'orderbook_snapshot' via `refresh` and 'orderbook_delta' via `update.
        Will default to previous state if message fields cannot be parsed.

        Attributes:
            data(dict): A dictionary that represents the data from a `orderbook_snapshot` or `orderbook_delta` message.
        """
        try:
            # Verify we can pull the update type
            update_type = data.get("type")

            if update_type is None:
                logger.error(f"Failed to get update type in data message: {data}")
                raise ValueError("Failed to get update type in data message")

            # Verify we can pull the seq data
            seq = data.get("seq")

            if seq is None:
                logger.error(f"Failed to find sequence in orderbook update: {data}")
                raise ValueError(
                    "Sequence number is missing in the orderbook data message"
                )

            # Overwrite the data
            data = data["msg"]

            match update_type:
                case "orderbook_snapshot":
                    # Our orderbook takes the "YES" perspective on the market. This means we interpret the "NO"
                    # best bid as the best ask for "YES". This is done by taking 100 - yes_bid_price.
                    bids = [Level(level[0], level[1]) for level in data["yes"]]
                    asks = [Level(100 - level[0], level[1]) for level in data["no"]]

                    # Refresh the book with the new snapshot data
                    self.orderbook.refresh("bids", bids, seq)
                    self.orderbook.refresh("asks", asks, seq)

                    # Log the successful processing of the snapshot
                    logger.info(
                        f"Orderbook created: {self.orderbook.bba} mid {self.orderbook.mid_price} micro {self.orderbook.micro_price:.2f} spread {self.orderbook.spread},"
                    )

                case "orderbook_delta":
                    if data["side"] == "yes":
                        delta = Delta(price=data["price"], delta=data["delta"])
                        self.orderbook.update(self.orderbook.bids, delta, seq)
                        logger.info(
                            f"Orderbook YES update: {self.orderbook.bba} mid {self.orderbook.mid_price} micro {self.orderbook.micro_price:.2f} spread {self.orderbook.spread}"
                        )

                    elif data["side"] == "no":
                        # Take the "YES" perspective and create the synthetic "YES" ask of 100-no_price
                        delta = Delta(price=100 - data["price"], delta=data["delta"])
                        self.orderbook.update(self.orderbook.asks, delta, seq)
                        logger.info(
                            f"Orderbook NO  update: {self.orderbook.bba} mid {self.orderbook.mid_price} micro {self.orderbook.micro_price:.2f} spread {self.orderbook.spread}"
                        )

        except Exception as e:
            raise Exception(f"Orderbook process error: {e}")
