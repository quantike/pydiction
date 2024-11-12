from typing import Dict, List, Optional, Tuple

from common.models.level import Level
from common.models.delta import Delta


class Orderbook:
    """
    Stores the Orderbook which is a collection of the current `bids` and `asks`.
    """

    def __init__(self, bids: List[Level], asks: List[Level]) -> None:
        self.bids = bids
        self.asks = asks

    @classmethod
    def empty(cls) -> "Orderbook":
        """
        Creates an empty Orderbook instance.

        Returns:
            Orderbook: An empty Orderbook instance.
        """
        return Orderbook(bids=[Level(0, 0)], asks=[Level(0, 0)])

    @property
    def is_empty(self) -> bool:
        """
        Checks if the current book is empty.

        Returns:
            bool: True if the book is empty, false otherwise.
        """
        return (self.bids == [Level(0, 0)]) & (self.asks == [Level(0, 0)])

    def sort(self) -> None:
        """
        Sorts bids and asks, with bids in reverse order.

        Some book sorts might remove levels past a certain depth, but books have a finite depth of 100 in prediction markets
        that we are concerned with (Kalshi).
        """
        self.bids.sort(
            key=lambda level: level.price, reverse=True
        )  # bids are typically sorted in reverse
        self.asks.sort(key=lambda level: level.price)

    def update(self, book: List[Level], delta: Delta) -> None:
        """
        Updated the book with any new delta. Intended use is with orderbook delta updates.

        Attributes:
            book(List[Level]): The bid or ask side of the book, represented as a list of levels (price, quantity).
            delta(Delta): The delta message used to update a specific level in the book, represented as (price, delta).
        """
        for i, level in enumerate(book):
            # If there is a matching price, update the quantity with the delta
            if delta.price == level.price:
                new_quanity = level.quantity + delta.delta

                # If positive, update quanitity at price level in book
                if new_quanity > 0:
                    book[i] = Level(level.price, new_quanity)

                # If zero (or negative), remove price level from book
                else:
                    book.pop(i)

                break

        # If there is no matching price in the book, append it to the book
        else:
            if delta.delta > 0:  # Delta should *always* be positive in this case
                book.append(Level(delta.price, delta.delta))

        # Sort the book
        self.sort()

    def refresh(self, side: str, snapshot: List[Level]) -> None:
        """
        Refreshes the book side by replacing the bids or asks with a snapshot. Intended use is with orderbook snaphot data.

        Attributes:
            side(str): String of either "bids" or "asks". Used to specify which side gets updated.
            snaphot(List[Level]): The list of price, quantity levels to be applied to the book side.
        """
        # Apply snapshot to correct book side
        match side:
            case "bids":
                self.bids = snapshot
            case "asks":
                self.asks = snapshot

        # Sort the book
        self.sort()

    def to_dict(self) -> Dict[str, List[Level]]:
        """
        Exports the current book data to a dictionary.
        """
        return {"bids": self.bids, "asks": self.asks}

    def calculate_vwap(self):
        raise NotImplementedError

    def calculate_imbalance(self):
        raise NotImplementedError

    def calculate_slippage(self):
        raise NotImplementedError

    @property
    def bba(self) -> Tuple[Optional[Level], Optional[Level]]:
        """
        Returns the best bid and ask levels, as a property.

        Returns:
            Tuple[Optional[Level], Optional[Level]]: A tuple of the best bid and ask.
        """
        return self.bids[0] if self.bids else None, self.asks[0] if self.asks else None

    @property
    def spread(self) -> Optional[int]:
        """
        Returns the spread, if any exists (the difference between the best ask and the best bid prices).

        Returns:
            Optional[int]: The spread value, if any exists.
        """
        best_bid, best_ask = self.bba

        # In the event we have both a best bid and best ask
        # calculate the spread
        if best_bid and best_ask:
            return best_ask.price - best_bid.price

        # In the event we do not have one of them return None
        return None

    @property
    def mid_price(self) -> Optional[float]:
        """
        Returns the mid price, if any exists (average between best bid and best ask prices).

        Returns:
            Optional[float]: The mid price, if any exists.
        """
        best_bid, best_ask = self.bba

        # In the event we have both a best bid and best ask
        # calculate the mid price
        if best_bid and best_ask:
            return (best_bid.price + best_ask.price) / 2.0

        # In the event we do not have one of them return None
        return None

    @property
    def micro_price(self) -> Optional[float]:
        """
        Returns the micro price, if any exists (the quantity-weighted mid price of the best bid and best ask).

        Calculated via: Pm = Pa * Qb / (Qa + Qb) + Pb * Qa / (Qa + Qb)

        Where:
            Pm: The micro price.
            Pa: The best ask price.
            Pb: The best bid price.
            Qa: The best ask quantity.
            Qb: The best bid quantity.

        Returns:
            Optional[float]: The micro price, if any exists.
        """
        best_bid, best_ask = self.bba

        # In the event we have both a best bid and best ask
        # calculate the mid price
        if best_bid and best_ask:
            return best_ask.price * best_bid.quantity / (
                best_ask.quantity + best_bid.quantity
            ) + best_bid.price * best_ask.quantity / (
                best_ask.quantity + best_bid.quantity
            )

        # In the event we do not have one of them return None
        return None
