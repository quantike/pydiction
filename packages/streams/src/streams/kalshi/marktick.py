from typing import Any, Dict
from common.models.tick import Tick


class KalshiTickHandler:

    def __init__(self, tick: Tick) -> None:
        self.tick = tick

    def process(self, data: Dict[str, Any]) -> None:
        """
        Attempts to update the market tick based on a data message. Defaults to prior value if value cannot be found for a key from the data.

        Attributes:
            data(dict): A dictionary that represents the data from a `tick` message.
        """
        try:
            self.tick.update(
                ts=data.get("ts", self.tick.ts),
                price=data.get("price", self.tick.price),
                bid=data.get("bid", self.tick.bid),
                ask=data.get("ask", self.tick.ask),
                volume=data.get("volume", self.tick.volume),
                oi=data.get("oi", self.tick.oi),
                dollar_volume=data.get("dollar_volume", self.tick.dollar_volume),
                dollar_oi=data.get("dollar_oi", self.tick.dollar_oi)
            )

        except Exception as e:
            raise Exception(f"Tick process error: {e}")
