from loguru import logger
from typing import Any, Dict

from kalshi.models.lifecycle import Lifecycle


class KalshiLifecycleHandler:
    def __init__(self, lifecycle: Lifecycle) -> None:
        self.lifecycle = lifecycle

    def process(self, data: Dict[str, Any]) -> None:
        """
        Attempts to update the market lifecycle based on a data message. Defaults to prior value if value cannot be found for a key from the data.

        Attributes:
            data(dict): A dictionary that represents the data from a `market_lifecycle` message.
        """
        try:
            self.lifecycle = Lifecycle(
                is_deactivated=data.get("is_deactivated", self.lifecycle.is_deactivated),
                open_ts=data.get("open_ts", self.lifecycle.open_ts),
                close_ts=data.get("close_ts", self.lifecycle.close_ts),
                determination_ts=data.get("determination_ts", self.lifecycle.determination_ts),
                settled_ts=data.get("settled_ts", self.lifecycle.settled_ts),
                result=data.get("result", self.lifecycle.result)
            )

            # Log the successful processing of the lifecycle update
            logger.info(
                f"Lifecycle: {self.lifecycle}"
            )

        except Exception as e:
            raise Exception(f"Lifecycle process error: {e}")
