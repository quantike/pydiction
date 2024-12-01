from typing import Tuple

from common.models.orderbook import Orderbook


class BookFeatures:
    def __init__(self, orderbook: Orderbook) -> None:
        self.orderbook = orderbook

    def spread(self) -> None | int:
        """
        Calculates the spread, if any, between the best ask and best bid. Returns the spread as an int, or None if there is no valid spread when the function is called.
        """
        if self.orderbook.bids and self.orderbook.asks:
            # We can access the zeroth index of this list since the book is always in a sorted state.
            # TODO: it might be smart to add an `.is_sorted()` method to the book?
            best_bid = self.orderbook.bids[0].price
            best_ask = self.orderbook.asks[0].price

            return best_ask - best_bid

        # Return None if there is not a valid spread
        return None

    def depth(self) -> Tuple[int, int]:
        """
        Calculates the sum of order quantities for both side of the orderbook. Returns a tuple with the (bid_depth, ask_depth).
        """
        bid_depth = sum(level.quantity for level in self.orderbook.bids)
        ask_depth = sum(level.quantity for level in self.orderbook.asks)

        return bid_depth, ask_depth
