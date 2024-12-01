from typing import Any, Dict

from common.models.trade import Trade
from loguru import logger


class KalshiTradeHandler:
    def __init__(self, trade: Trade) -> None:
        self.trade = trade

    def process(self, data: Dict[str, Any]) -> None:
        """
        Attempts to update the market trade based on a data message. Defaults to prior value if value cannot be found for a key from the data.

        Attributes:
            data(dict): A dictionary that represents the data from a `trade` message.
        """
        try:
            self.trade = Trade(
                ts=data.get("ts", self.trade.ts),
                side=data.get("taker_side", self.trade.side),
                yes_price=data.get("yes_price", self.trade.yes_price),
                no_price=data.get("no_price", self.trade.no_price),
                count=data.get("count", self.trade.count),
            )

            # Log the successful processing of the tick
            logger.info(
                f"Trade processed {self.trade.side}: {self.trade.yes_price if self.trade.side == "yes" else self.trade.no_price} for {self.trade.count} @ {self.trade.ts}"
            )

        except Exception as e:
            raise Exception(f"Tick process error: {e}")
