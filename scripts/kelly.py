# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fire",
# ]
# ///
from typing import Literal

import fire

Side = Literal["YES", "NO"]


def _kelly_fraction(side: Side, ps: int, k: int) -> float:
    """
    Full-Kelly fraction of bankroll for a single take-and-hold trade.

    Args:
        side (Side): "YES" for long-YES / short-NO, "NO" for long-NO / short-YES
        ps (int): Subjective probability the event resolves to YES (0-100)
        k (int): Executable price in *cents* between 0 and 100 (e.g. 42 cents for $0.42)

    Returns:
        Optimal Kelly fraction of bankroll that should be bet to maximize the long-run exponential
        growth rate of capital
    """
    if side == "YES":
        return float((ps - k) / (100 - k))
    else:
        return float(((100 - ps) - k) / (100 - k))


class KellyCLI:
    def bet(
        self,
        side: Side,
        ps: int,
        k: int,
        bankroll: float,
        kelly: float = 1.0,
        is_bid: bool = False,
    ) -> int:
        """
        Returns the integer contract count suggested by Kelly sizing.

        Args:
            side (Side): "YES" if you want to buy YES (or short NO), "NO" if you want to buy NO (or short YES)
            ps (int): Subjective probability the event resolves to YES (0-100)
            k (int): Executable price in *cents* between 0 and 100 (ask for buying, bid for selling)
            bankroll (float): Current liquid bankroll in dollars
            kelly (float): Fractional Kelly multiplier, 1=full Kelly, 0.5=half, 0.25=quarter, ...
            is_bid (bool): set True if *selling/shorting* against the bid instead of buying

        Returns:
            The integer contract count suggested by Kelly sizing.
        """
        f_full = _kelly_fraction(side, ps, k)

        # edge gone -> no trade
        if f_full <= 0:
            return 0

        stake_dollars = bankroll * kelly * f_full  # cents to risk
        price_dollars = k / 100
        contracts = int(stake_dollars / price_dollars)  # whole contracts

        # selling or shorting
        if is_bid:
            contracts *= -1

        return contracts


if __name__ == "__main__":
    fire.Fire(KellyCLI)
