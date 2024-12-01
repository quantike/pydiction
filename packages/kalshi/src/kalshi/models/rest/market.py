from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


@dataclass
class Series:
    pass


@dataclass
class Event:
    pass

class MarketType(Enum):
    BINARY = "binary"
    SCALAR = "scalar"

class MarketStrikeType(Enum):
    UNKOWN = "unkown"
    GREATER = "greater"
    LESS = "less"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    BETWEEN = "between"
    FUNCTIONAL = "functional"
    CUSTOM = "custom"

class MarketPriceUnits(Enum):
    CENT = "usd_cent"
    CENTICENT = "usd_centi_cent"

class MarketResult(Enum):
    UNDETERMINED = ""
    YES = "yes"
    NO = "no"
    VOID = "void"
    ALL_YES = "all_yes"
    ALL_NO = "all_no"

@dataclass
class Market:
    can_close_early: bool
    category: str
    close_time: datetime
    event_ticker: str
    expiration_time: datetime
    expiration_value: str
    floor_strike: float
    last_price: int
    latest_expiration_time: datetime
    liquidity: int
    market_type: MarketType
    no_ask: int
    no_bid: int
    no_sub_title: str
    notional_value: int
    open_interest: int
    open_time: datetime
    previous_price: int
    previous_yes_ask: int
    previous_yes_bid: int
    response_price_units: MarketPriceUnits
    result: MarketResult
    risk_limit_cents: int
    rules_primary: str
    rules_secondary: str
    settlement_timer_seconds: int
    status: str
    strike_type: MarketStrikeType
    subtitle: str
    tick_size: int
    ticker: str
    title: str
    volume: int
    volume_24h: int
    yes_ask: int
    yes_bid: int
    yes_sub_title: str
    custom_strike: Optional[Dict[str, Any]] = None
    functional_strike: Optional[str] = None
    expected_expiration_time: Optional[datetime] = None
    fee_waiver_expiration_time: Optional[datetime] = None
    settlement_value: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Market':
        return cls(
            can_close_early=data['can_close_early'],
            category=data['category'],
            close_time=datetime.fromisoformat(data['close_time']),
            event_ticker=data['event_ticker'],
            expiration_time=datetime.fromisoformat(data['expiration_time']),
            expiration_value=data['expiration_value'],
            floor_strike=data['floor_strike'],
            last_price=data['last_price'],
            latest_expiration_time=datetime.fromisoformat(data['latest_expiration_time']),
            liquidity=data['liquidity'],
            market_type=MarketType(data['market_type']),
            no_ask=data['no_ask'],
            no_bid=data['no_bid'],
            no_sub_title=data['no_sub_title'],
            notional_value=data['notional_value'],
            open_interest=data['open_interest'],
            open_time=datetime.fromisoformat(data['open_time']),
            previous_price=data['previous_price'],
            previous_yes_ask=data['previous_yes_ask'],
            previous_yes_bid=data['previous_yes_bid'],
            response_price_units=MarketPriceUnits(data['response_price_units']),
            result=MarketResult(data['result']),
            risk_limit_cents=data['risk_limit_cents'],
            rules_primary=data['rules_primary'],
            rules_secondary=data['rules_secondary'],
            settlement_timer_seconds=data['settlement_timer_seconds'],
            status=data['status'],
            strike_type=MarketStrikeType(data['strike_type']),
            subtitle=data['subtitle'],
            tick_size=data['tick_size'],
            ticker=data['ticker'],
            title=data['title'],
            volume=data['volume'],
            volume_24h=data['volume_24h'],
            yes_ask=data['yes_ask'],
            yes_bid=data['yes_bid'],
            yes_sub_title=data['yes_sub_title'],
            custom_strike=data['custom_strike'] if 'custom_strike' in data else None,
            functional_strike=data.get('functional_strike'),
            expected_expiration_time=datetime.fromisoformat(data['expected_expiration_time']) if 'expected_expiration_time' in data else None,
            fee_waiver_expiration_time=datetime.fromisoformat(data['fee_waiver_expiration_time']) if 'fee_waiver_expiration_time' in data else None,
            settlement_value=data.get('settlement_value')
        )


@dataclass
class Trade:
    pass
