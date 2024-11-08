from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass
class Tick:
    """
    Represents a tick message that provides the current list price for a market.

    Attributes:
        ts(datetime): The timestamp of when the tick update happened.
        price(int): The last price in the market when the ticker update happened. Between 1 and 99 (inclusive).
        bid(int): Current best bid on the "Yes" market. Between 1 and 99 (inclusive).
        ask(int): Current best ask on the "Yes" market. Between 1 and 99 (inclusive).
        volume(int): Total volume of individual contracts traded on the market so far.
        oi(int): Number of active contracts in the market currently.
        dollar_volume(int): Number of dollars traded on the market so far.
        dollar_oi(int): Number of dollars positioned in the market current.
    """

    ts: datetime
    price: int
    bid: int
    ask: int
    volume: int
    oi: int
    dollar_volume: int
    dollar_oi: int

    def update(self, ts: datetime, price: int, bid: int, ask: int, volume: int, oi: int, dollar_volume: int, dollar_oi: int) -> None:
        """
        Updates the `Tick` dataclass in-place if there is a change. We may want to check if this is faster than just a full re-write of the data.

        Attributes:
            ts(datetime): The timestamp of when the tick update happened.
            price(int): The last price in the market when the ticker update happened. Between 1 and 99 (inclusive).
            bid(int): Current best bid on the "Yes" market. Between 1 and 99 (inclusive).
            ask(int): Current best ask on the "Yes" market. Between 1 and 99 (inclusive).
            volume(int): Total volume of individual contracts traded on the market so far.
            oi(int): Number of active contracts in the market currently.
            dollar_volume(int): Number of dollars traded on the market so far.
            dollar_oi(int): Number of dollars positioned in the market current.
        """
        if self.ts != ts:
            self.ts = ts
        if self.price != price:
            self.price = price
        if self.bid != bid: 
            self.bid = bid
        if self.ask != ask:
            self.ask = ask
        if self.volume != volume:
            self.volume = volume
        if self.oi != oi:
            self.oi = oi
        if self.dollar_volume != dollar_volume:
            self.dollar_volume = dollar_volume
        if self.dollar_oi != dollar_oi:
            self.dollar_oi = dollar_oi

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.ts,
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "volume": self.volume,
            "oi": self.oi,
            "dollar_volume": self.dollar_volume,
            "dollar_oi": self.dollar_oi,
        }