from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Lifecycle:
    """
    Represents a market lifecycle message that updates the client on the market state.

    Attributes:
        is_deactivated(bool):
        open_ts(int): Unix timestamp for when the market opened (in seconds).
        close_ts(int): Unix timestamp for when the market is scheduled to close (in seconds). Will be updated in case of early determination markets.
        determination_ts(Optional[int]): This key will not exist before the market is determined. Unix timestamp for when the market is determined (in seconds).
        settled_ts(Optional[int]): This key will not exist before the market is settled. Unix timestamp for when the market is settled (in seconds).
        result(Optional[str]): This key will not exist before the market is determined. Result of the market. Either "yes" or "no".
    """

    is_deactivated: bool
    open_ts: int
    close_ts: int
    determination_ts: Optional[int] = None
    settled_ts: Optional[int] = None
    result: Optional[str] = None
    
    @classmethod
    def empty(cls) -> "Lifecycle":
        """
        Creates an empty `Lifecycle` instance with placeholder values.
        """
        return cls(
            # We consider empty markets deactivated for trading logic
            is_deactivated=True, open_ts=0, close_ts=0
        )

    def update(
        self,
        is_deactivated: bool,
        open_ts: int,
        close_ts: int,
        determination_ts: Optional[bool] = None,
        settled_ts: Optional[bool] = None,
        result: Optional[str] = None
    ) -> None:
        """
        Updates the `Lifecycle` dataclass in-place if there is a change. We may want to check if this is faster than just a full re-write of the data.

        Attributes:
            is_deactivated(bool):
            open_ts(int): Unix timestamp for when the market opened (in seconds).
            close_ts(int): Unix timestamp for when the market is scheduled to close (in seconds). Will be updated in case of early determination markets.
            determination_ts(Optional[int]): This key will not exist before the market is determined. Unix timestamp for when the market is determined (in seconds).
            settled_ts(Optional[int]): This key will not exist before the market is settled. Unix timestamp for when the market is settled (in seconds).
            result(Optional[str]): This key will not exist before the market is determined. Result of the market. Either "yes" or "no".
        """
        if self.is_deactivated != is_deactivated:
            self.is_deactivated = is_deactivated
        if self.open_ts != open_ts:
            self.open_ts = open_ts
        if self.close_ts != close_ts:
            self.close_ts = close_ts
        if self.determination_ts != determination_ts:
            self.determination_ts = determination_ts
        if self.settled_ts != settled_ts:
            self.settled_ts = settled_ts
        if self.result != result:
            self.result = result

    def to_dict(self) -> Dict[str, Any]:
        """
        Creates a dictionary from the current lifecycle data.
        """
        return {
            "is_deactivated": self.is_deactivated,
            "open_ts": self.open_ts,
            "close_ts": self.close_ts,
            "determination_ts": self.determination_ts,
            "settled_ts": self.settled_ts,
            "result": self.result
        }
