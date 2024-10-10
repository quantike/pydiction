from collections import namedtuple
from typing import Dict, List


Level = namedtuple("Level", ["price", "quantity"])
Delta = namedtuple("Delta", ["price", "delta"])


class Orderbook:
    """
    Stores the Orderbook which is a collection of the current `bids` and `asks`.
    """

    def __init__(self, bids: List[Level], asks: List[Level]) -> None:
        self.bids = bids
        self.asks = asks

    def sort(self) -> None:
        """
        Sorts bids and asks, with bids in reverse order.

        Some book sorts might remove levels past a certain depth, but books have a finite depth of 100 in prediction markets.
        """
        self.bids.sort(
            key=lambda level: level.price, reverse=True
        )  # bids are typically sorted in reverse
        self.asks.sort(key=lambda level: level.price)

    def update(self, book: List[Level], delta: Delta) -> None:
        """
        Updated the book with any new delta.

        TODO: "orderbook_delta" messages always come one-at-a-time so we do not need to use `List[Delta]`
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
        Refreshes the book side by replacing the bids or asks with a snapshot.
        """
        # Apply snapshot to correct book side
        match side:
            case "bids":
                self.bids = snapshot
            case "asks":
                self.asks = snapshot
            case _:
                print("Encountered undefined `side` while applying orderbook refresh")

        # Sort the book
        self.sort()

    def process(self, recv: Dict) -> None:
        """
        Handles incoming WebSocket messages from the "orderbook_delta" channel.

        Messages will be of `"type": "orderbook_snapshot"|"orderbook_delta"` in the `recv` dictionary.
        """
        match recv["type"]:
            case "orderbook_snapshot":
                # Create book for "yes" and "no", if they exist
                yes_levels = [
                    Level(level[0], level[1]) for level in recv["msg"].get("yes", [])
                ]
                no_levels = [
                    Level(level[0], level[1]) for level in recv["msg"].get("no", [])
                ]

                # If there are elements, refresh book
                if yes_levels:
                    self.refresh(side="bids", snapshot=yes_levels)
                if no_levels:
                    self.refresh(side="asks", snapshot=no_levels)

                print("snapshot processed")

            case "orderbook_delta":
                # Create the Delta object
                delta = Delta(recv["msg"]["price"], recv["msg"]["delta"])

                # Update the correct side of the book
                if recv["msg"]["side"] == "yes":
                    self.update(self.bids, delta=delta)
                elif recv["msg"]["side"] == "no":
                    self.update(self.asks, delta=delta)

                print("delta processed")

            case _:
                print("unknown element encountered")
