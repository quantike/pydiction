from dataclasses import dataclass
from typing import Dict


@dataclass
class Trade:
    """
    Represents a trade message for a prediction market.

    Attributes:
        ts(int): The timestamp of when the trade occurred.
        side(str): Side of the taker user on this trade, either "yes" or "no".
        yes_price(int): Price for the trade. Between 1 and 99 (inclusive).
        no_price(int): Price for the trade. Between 1 and 99 (inclusive).
        count(int): The number of contracts traded.
    """

    ts: int
    side: str
    yes_price: int
    no_price: int
    count: int

    @classmethod
    def empty(cls) -> 'Trade':
        """
        Creates an empty `Trade` instance with default parameters.
        """
        return Trade(
            ts=0,
            side="fake",
            yes_price=0,
            no_price=0,
            count=0
        )

    def to_dict(self) -> Dict[str, int|str]:
        return {
            "ts": self.ts,
            "side": self.side,
            "yes_price": self.yes_price,
            "no_price": self.no_price,
            "count": self.count,
        }
