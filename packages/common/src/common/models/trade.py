from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

@dataclass
class Trade:
    """
    Represents a trade message for a prediction market.

    Attributes:
        ts(datetime): The timestamp of when the trade occurred.
        side(str): Side of the taker user on this trade, either "yes" or "no".
        price(int): Price for the trade. Between 1 and 99 (inclusive).
        amount(int): The number of contracts traded.
    """
    ts: datetime
    side: str
    price: int
    amount: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.ts,
            "side": self.side,
            "price": self.price,
            "amount": self.amount
        }
