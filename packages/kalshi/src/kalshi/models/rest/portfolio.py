from enum import Enum
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional
from datetime import datetime


class OrderAction(Enum):
    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "OrderActionUnknown"


class OrderSide(Enum):
    YES = "yes"
    NO = "no"
    UNSET = "SIDE_UNSET"


@dataclass
class PortfolioBalance:
    balance: int
    payout: int


@dataclass
class Fill:
    ticker: str
    created_time: int
    side: OrderSide
    action: OrderAction
    yes_price: int
    no_price: int
    count: int
    is_taker: bool
    order_id: str
    trade_id: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Fill":
        """
        Converts a dictionary to a Fill dataclass instance.

        Args:
            data (Dict[str, Any]): The dictionary containing fill data.

        Returns:
            Fill: A fill dataclass instance.
        """
        return cls(
            ticker=data["ticker"],
            created_time=int(datetime.fromisoformat(data["created_time"]).timestamp()),
            side=OrderSide(data["side"]),
            action=OrderAction(data["action"]),
            yes_price=data["yes_price"],
            no_price=data["no_price"],
            count=data["count"],
            is_taker=data["is_taker"],
            order_id=data["order_id"],
            trade_id=data["trade_id"],
        )


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    UNKNOWN = "OrderTypeUnknown"


class OrderStatus(Enum):
    RESTING = "resting"
    CANCELED = "canceled"
    EXECUTED = "executed"
    PENDING = "pending"


@dataclass
class Order:
    order_id: str
    client_order_id: str
    order_group_id: str
    user_id: str  # Enforce a user to provide an ID for orders
    ticker: str
    action: OrderAction
    side: OrderSide
    type: OrderType
    status: OrderStatus
    no_price: int
    yes_price: int
    created_time: int
    last_update_time: Optional[int] = None
    expiration_time: Optional[int] = None
    amend_count: Optional[int] = None
    amend_taker_fill_count: Optional[int] = None
    close_cancel_count: Optional[int] = None
    decrease_count: Optional[int] = None
    fcc_cancel_count: Optional[int] = None
    maker_fees: Optional[int] = None
    maker_fill_cost: Optional[int] = None
    maker_fill_count: Optional[int] = None
    maker_self_trade_cancel_count: Optional[int] = None
    place_count: Optional[int] = None
    queue_position: Optional[int] = None
    remaining_count: Optional[int] = None
    self_trade_prevention_type: Optional[Any] = None
    taker_fees: Optional[int] = None
    taker_fill_cost: Optional[int] = None
    taker_fill_count: Optional[int] = None
    taker_self_trade_cancel_count: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Order":
        """
        Converts a dictionary to an Order dataclass instance.

        Args:
            data (Dict[str, Any]): The dictionary containing order data.

        Returns:
            Order: An Order dataclass instance.
        """
        return cls(
            order_id=data["order_id"],
            client_order_id=data["client_order_id"],
            order_group_id=data["order_group_id"],
            user_id=data["user_id"],
            ticker=data["ticker"],
            action=OrderAction(data["action"]),
            side=OrderSide(data["side"]),
            type=OrderType(data["type"]),
            status=OrderStatus(data["status"]),
            no_price=data["no_price"],
            yes_price=data["yes_price"],
            created_time=int(datetime.fromisoformat(data["created_time"]).timestamp()),
            last_update_time=int(
                datetime.fromisoformat(data["last_update_time"]).timestamp()
            )
            if "last_update_time" in data
            else None,
            expiration_time=int(
                datetime.fromisoformat(data["expiration_time"]).timestamp()
            )
            if "expiration_time" in data
            else None,
            amend_count=data.get("amend_count"),
            amend_taker_fill_count=data.get("amend_taker_fill_count"),
            close_cancel_count=data.get("close_cancel_count"),
            decrease_count=data.get("decrease_count"),
            fcc_cancel_count=data.get("fcc_cancel_count"),
            maker_fees=data.get("maker_fees"),
            maker_fill_cost=data.get("maker_fill_cost"),
            maker_fill_count=data.get("maker_fill_count"),
            maker_self_trade_cancel_count=data.get("maker_self_trade_cancel_count"),
            place_count=data.get("place_count"),
            queue_position=data.get("queue_position"),
            remaining_count=data.get("remaining_count"),
            self_trade_prevention_type=data.get("self_trade_prevention_type"),
            taker_fees=data.get("taker_fees"),
            taker_fill_cost=data.get("taker_fill_cost"),
            taker_fill_count=data.get("taker_fill_count"),
            taker_self_trade_cancel_count=data.get("taker_self_trade_cancel_count"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts an Order dataclass instance to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the Order instance.
        """
        data = asdict(self)
        data["action"] = self.action.value
        data["side"] = self.side.value
        data["type"] = self.type.value
        data["status"] = self.status.value
        return data


@dataclass
class EventPosition:
    event_ticker: str
    event_exposure: int
    resting_order_count: int
    realized_pnl: int
    total_cost: int
    fees_paid: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventPosition":
        """
        Converts a dictionary to a EventPosition dataclass instance.

        Args:
            data (Dict[str, Any]): The dictionary containing event position data.

        Returns:
            EventPosition: A EventPosition dataclass instance.
        """
        return cls(
            event_ticker=data["event_ticker"],
            event_exposure=data["event_exposure"],
            resting_order_count=data["resting_order_count"],
            realized_pnl=data["realized_pnl"],
            total_cost=data["total_cost"],
            fees_paid=data["fees_paid"],
        )


class MarketSide(Enum):
    YES = "yes"
    NO = "no"
    NEUTRAL = "neutral"


@dataclass
class MarketPosition:
    ticker: str
    position: int
    market_exposure: int
    resting_orders_count: int
    realized_pnl: int
    total_traded: int
    fees_paid: int
    last_updated_ts: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketPosition":
        """
        Converts a dictionary to a MarketPosition dataclass instance.

        Args:
            data (Dict[str, Any]): The dictionary containing market position data.

        Returns:
            MarketPosition: A MarketPosition dataclass instance.
        """
        return cls(
            ticker=data["ticker"],
            position=data["position"],
            market_exposure=data["market_exposure"],
            resting_orders_count=data["resting_orders_count"],
            realized_pnl=data["realized_pnl"],
            total_traded=data["total_traded"],
            fees_paid=data["fees_paid"],
            last_updated_ts=int(
                datetime.fromisoformat(data["last_updated_ts"]).timestamp()
            ),
        )

    @property
    def side(self) -> MarketSide:
        if self.position > 0:
            return MarketSide.YES
        elif self.position < 0:
            return MarketSide.NO
        else:
            return MarketSide.NEUTRAL


@dataclass
class Settlement:
    ticker: str
    settled_time: int
    market_result: str
    no_count: int
    no_total_cost: int
    yes_count: int
    yes_total_cost: int
    revenue: int
