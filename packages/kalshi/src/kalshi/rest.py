from typing import Any, Dict, List, Optional
from loguru import logger

import requests
from common.state import State

from kalshi.authentication import Authenticator
from kalshi.models.rest.market import Market
from kalshi.models.rest.portfolio import (
    EventPosition,
    Fill,
    MarketPosition,
    Order,
    OrderStatus,
    PortfolioBalance,
)


class KalshiRestClient:
    def __init__(self, state: State) -> None:
        """
        Initializes the Kalshi REST client with the given state and authenticator.

        Args:
            state (State): The shared state object containing configurations and parameters.
        """
        self.state = state
        self.auth = Authenticator(self.state)
        self.is_connected = self._connect_()

    def _connect_(self) -> bool:
        """
        Connects to the Kalshi REST API using authentication credentials.

        Returns:
            bool: True if the login attempt is successful, False otherwise.
        """
        # Retrieve the response body from a login attempt
        login_response: Dict[str, str] = self.auth.get_auth_headers_rest(
            self.state.rest_base_url
        )

        # If the "token" response object exists, return True
        if login_response.get("token"):
            return True

        # Else, login failed
        return False

    def _deep_fetch_(
        self,
        path: str,
        key: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Helper function that performs a deep fetch via pagination of results.

        Args:
            path (str): The API endpoint path to fetch from.
            key (str): The key in the JSON response containing the list of items to fetch.
            params (Optional[Dict[str, Any]]): Optional dictionary of query parameters.
            headers (Optional[Dict[str, Any]]): Optional dictionary of headers.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the fetched items.
        """
        if params is None:
            params = {}

        results = []
        next_cursor = None

        while True:
            if next_cursor:
                params["cursor"] = next_cursor

            response = requests.get(
                self.state.rest_base_url + path, params=params, headers=headers
            )
            response.raise_for_status()

            data = response.json()

            if key in data:
                results.extend(data[key])
            else:
                print(f"No `{key}` found in response")

            next_cursor = data.get("cursor")

            # If there's no next_cursor we break pagination
            if not next_cursor:
                break

        return results

    def get_series(self, series_ticker: str):
        """
        Retrieves details for a given series by its ticker.

        Args:
            series_ticker (str): The series ticker to fetch details for.

        Returns:
            Response: The HTTP response object containing the series details.
        """
        path = f"/trade-api/v2/series/{series_ticker}"

        return requests.get(self.state.rest_base_url + path)

    def get_events(
        self,
        series_ticker: Optional[str] = None,
        status: Optional[str] = None,
        with_nested_markets: bool = False,
        fetch_all: bool = False,
    ):
        """
        Retrieves a list of events, optionally filtered by parameters.

        Args:
            series_ticker (Optional[str]): The ticker of the series to filter events by.
            status (Optional[str]): The status to filter events by.
            with_nested_markets (bool): Whether to include nested markets in the response.
            fetch_all (bool): Whether to fetch all pages of results.

        Returns:
            List[Dict[str, Any]]: A list of event dictionaries if fetch_all is True.
            Otherwise, returns a list of markets.
        """
        path = "/trade-api/v2/events"

        # HACK: Optional construction of params from function arguments
        params = {
            k: v
            for k, v in {
                "series_ticker": series_ticker,
                "status": status,
                "with_nested_markets": with_nested_markets,
            }.items()
            if v is not None
        }

        if fetch_all:
            return self._deep_fetch_(path, params=params, key="events")

        # Single fetch if fetch_all is false
        response = requests.get(self.state.rest_base_url + path, params=params)
        response.raise_for_status()
        data = response.json()

        return data.get("markets", [])

    def get_event(self, event_ticker: str):
        """
        Retrieves details for a given event by its ticker.

        Args:
            event_ticker (str): The event ticker to fetch details for.

        Returns:
            Response: The HTTP response object containing the event details.
        """
        path = f"/trade-api/v2/events/{event_ticker}"

        return requests.get(self.state.rest_base_url + path)

    def get_markets(
        self,
        event_ticker: Optional[str] = None,
        series_ticker: Optional[str] = None,
        status: Optional[str] = None,
        tickers: Optional[str] = None,
        fetch_all: bool = False,
    ):
        """
        Retrieves a list of markets, optionally filtered by parameters.

        Args:
            event_ticker (Optional[str]): The ticker of the event to filter markets by.
            series_ticker (Optional[str]): The ticker of the series to filter markets by.
            status (Optional[str]): The status to filter markets by.
            tickers (Optional[str]): Specific market tickers to filter by.
            fetch_all (bool): Whether to fetch all pages of results.

        Returns:
            List[Dict[str, Any]]: A list of market dictionaries if fetch_all is True.
            Otherwise, returns a list of markets.
        """
        if not self.is_connected:
            raise Exception("User not logged in")

        method = "GET"
        path = "/trade-api/v2/markets"
        headers = self.auth.create_headers(method, path)

        # Optional construction of params from function arguments
        params = {
            k: v
            for k, v in {
                "event_ticker": event_ticker,
                "series_ticker": series_ticker,
                "status": status,
                "tickers": tickers,
            }.items()
            if v is not None
        }

        if fetch_all:
            markets_data = self._deep_fetch_(
                path, params=params, headers=headers, key="markets"
            )
        else:
            # Single fetch if fetch_all is False
            response = requests.get(
                self.state.rest_base_url + path, params=params, headers=headers
            )
            response.raise_for_status()
            markets_data = response.json().get("markets", [])

        markets = [Market.from_dict(market_data) for market_data in markets_data]
        return markets

    def get_market(self, market_ticker: str):
        """
        Retrieves details for a given market by its ticker.

        Args:
            market_ticker (str): The market ticker to fetch details for.

        Returns:
            Response: The HTTP response object containing the market details.
        """
        method = "GET"
        path = f"/trade-api/v2/markets/{market_ticker}"

        headers = self.auth.create_headers(method, path)
        response = requests.get(self.state.rest_base_url + path, headers=headers)
        response.raise_for_status()

        market_data = response.json().get("market", {})
        logger.debug(market_data)

        return Market.from_dict(market_data)


    def get_market_trades(self, ticker: str, fetch_all: bool = False):
        """
        Retrieves a list of trades for a given market ticker.

        Args:
            ticker (str): The ticker of the market to fetch trades for.
            fetch_all (bool): Whether to fetch all pages of results.

        Returns:
            List[Dict[str, Any]]: A list of trade dictionaries.
        """
        # Wrapper around _deep_fetch_ for getting market trades
        path = "/trade-api/v2/markets/trades"
        params = {"ticker": ticker}

        if fetch_all:
            return self._deep_fetch_(path, params=params, key="trades")

        # Single fetch if fetch_all is False
        response = requests.get(self.state.rest_base_url + path, params=params)
        response.raise_for_status()
        data = response.json()

        return data.get("trades", [])

    def get_exchange_schedule(self) -> Dict[str, Any]:
        """
        Requests the exchange schedule.

        Returns:
            Dict[str, Any]: A dictionary containing the exchange schedule.
        """
        path = "/trade-api/v2/exchange/schedule"
        response = requests.get(self.state.rest_base_url + path)
        response.raise_for_status()
        return response.json()

    def get_exchange_status(self) -> Dict[str, Any]:
        """
        Requests the current exchange status.

        WARNING: This is an undocumented endpoint I happened upon.

        Returns:
            Dict[str, Any]: A dictionary containing the exchange status.
        """
        path = "/trade-api/v2/exchange/status"
        response = requests.get(self.state.rest_base_url + path)
        response.raise_for_status()
        return response.json()

    def get_exchange_announcements(self) -> Dict[str, Any]:
        """
        Requests exchange announcements, if any.

        Returns:
            Dict[str, Any]: A dictionary containing the exchange announcements.
        """
        path = "/trade-api/v2/exchange/announcements"
        response = requests.get(self.state.rest_base_url + path)
        response.raise_for_status()
        return response.json()

    def get_portfolio_balance(self) -> PortfolioBalance:
        """
        Requests the portfolio balance for a logged-in user.

        Returns:
            PortfolioBalance: A PortfolioBalance instance.
        """
        if not self.is_connected:
            raise Exception("User not logged in")

        method = "GET"
        path = "/trade-api/v2/portfolio/balance"
        headers = self.auth.create_headers(method, path)

        response = requests.get(self.state.rest_base_url + path, headers=headers)
        response.raise_for_status()
        pf_balance_data = response.json()

        return PortfolioBalance(
            balance=pf_balance_data.get("balance", 0),
            payout=pf_balance_data.get("payout", 0),
        )

    def get_fills(
        self,
        ticker: Optional[str] = None,
        order_id: Optional[str] = None,
        fetch_all: bool = False,
    ) -> List[Fill]:
        """
        Retrieves a list of fills for a given portfolio ticker.

        Args:
            ticker (Optional[str]): The ticker to fetch fills for.
            order_id (Optional[str]): The trade order ID.
            fetch_all (bool): Whether to fetch all pages of results.

        Returns:
            List[Fill]: A list of Fill instances.
        """
        if not self.is_connected:
            raise Exception("User not logged in")

        method = "GET"
        path = "/trade-api/v2/portfolio/fills"
        headers = self.auth.create_headers(method, path)

        # Optional construction of params from function arguments
        params = {
            k: v
            for k, v in {
                "ticker": ticker,
                "order_id": order_id,
            }.items()
            if v is not None
        }

        if fetch_all:
            fills_data = self._deep_fetch_(
                path, params=params, headers=headers, key="fills"
            )
        else:
            # Single fetch if fetch_all is False
            response = requests.get(
                self.state.rest_base_url + path, params=params, headers=headers
            )
            response.raise_for_status()
            fills_data = response.json().get("fills", [])

        fills = [Fill.from_dict(fill_data) for fill_data in fills_data]
        return fills

    def get_event_positions(
        self, event_ticker: Optional[str] = None, fetch_all: bool = False
    ) -> List[EventPosition]:
        """
        Retrieves a list of EventPositions for a given even ticker.

        Args:
            event_ticker (Optional[str]): The event ticker to fetch EventPositions.
            fetch_all (bool): Whether to fetch all pages of results.

        Returns:
            List[EventPosition]: A list of EventPosition instances.
        """
        if not self.is_connected:
            raise Exception("User not logged in")

        method = "GET"
        path = "/trade-api/v2/portfolio/positions"
        headers = self.auth.create_headers(method, path)

        # Optional construction of params from function arguments
        params = {
            k: v
            for k, v in {
                "event_ticker": event_ticker,
            }.items()
            if v is not None
        }

        if fetch_all:
            event_positions_data = self._deep_fetch_(
                path, params=params, headers=headers, key="event_positions"
            )
        else:
            # Single fetch if fetch_all is False
            response = requests.get(
                self.state.rest_base_url + path, params=params, headers=headers
            )
            response.raise_for_status()
            event_positions_data = response.json().get("event_positions", [])

        event_positions = [
            EventPosition.from_dict(event_position_data)
            for event_position_data in event_positions_data
        ]
        return event_positions

    def get_market_positions(
        self,
        ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        count_filter: Optional[str] = None,
        settlement_status: Optional[str] = None,
        fetch_all: bool = False,
    ) -> List[MarketPosition]:
        """
        Retrieves a list of MarketPositions for a given event ticker.

        Args:
            ticker (Optional[str]): The ticker for the MarketPosition.
            event_ticker (Optional[str]): The event ticker to fetch MarketPositions.
            count_filter (Optional[str]): Restricts the positions to those with any of following fields with non-zero values, as a comma separated list. The following values are accepted: position, total_traded, resting_order_count.
            settlement_status (Optional[str]): Settlement status of the markets to return. Defaults to unsettled. The following values are accepted: all, settled, unsettled.
            fetch_all (bool): Whether to fetch all pages of results.

        Returns:
            List[MarketPosition]: A list of MarketPosition instances.
        """
        if not self.is_connected:
            raise Exception("User not logged in")

        method = "GET"
        path = "/trade-api/v2/portfolio/positions"
        headers = self.auth.create_headers(method, path)

        # Optional construction of params from function arguments
        params = {
            k: v
            for k, v in {
                "ticker": ticker,
                "event_ticker": event_ticker,
                "count_filter": count_filter,
                "settlement_status": settlement_status,
            }.items()
            if v is not None
        }

        if fetch_all:
            market_positions_data = self._deep_fetch_(
                path, params=params, headers=headers, key="market_positions"
            )
        else:
            # Single fetch if fetch_all is False
            response = requests.get(
                self.state.rest_base_url + path, params=params, headers=headers
            )
            response.raise_for_status()
            market_positions_data = response.json().get("market_positions", [])

        market_positions = [
            MarketPosition.from_dict(market_position_data)
            for market_position_data in market_positions_data
        ]
        return market_positions

    def get_orders(
        self,
        ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        fetch_all: bool = False,
    ) -> List[Order]:
        """
        Retrieves a list of Orders for a given ticker.

        Args:
            ticker (Optional[str]): The ticker for the Order.
            event_ticker (Optional[str]): The event ticker to fetch Orders.
            status (Optional[OrderStatus]): Restricts the response to orders that have a certain status: resting, canceled, or executed.           
            fetch_all (bool): Whether to fetch all pages of results.

        Returns:
            List[Order]: A list of Order instances.
        """
        if not self.is_connected:
            raise Exception("User not logged in")

        method = "GET"
        path = "/trade-api/v2/portfolio/orders"
        headers = self.auth.create_headers(method, path)

        # Optional construction of params from function arguments
        params = {
            k: v
            for k, v in {
                "ticker": ticker,
                "event_ticker": event_ticker,
                "status": status,
            }.items()
            if v is not None
        }

        if fetch_all:
            orders_data = self._deep_fetch_(
                path, params=params, headers=headers, key="orders"
            )
        else:
            # Single fetch if fetch_all is false
            response = requests.get(
                self.state.rest_base_url + path, params=params, headers=headers
            )
            response.raise_for_status()
            orders_data = response.json().get("orders", [])

        # Convert the list of order dictionaries to a list of Order dataclass instances
        orders = [Order.from_dict(order_data) for order_data in orders_data]
        return orders

    def get_order(self, order_id: str) -> Order:
        """
        Fetches a single Order with an order_id.

        Args:
            order_id (str): Order ID input for the desired order. Should look like a UUIDv4 str.
        
        Returns:
            Order: The requested Order instance.
        """
        if not self.is_connected:
            raise Exception("User not logged in")

        method = "GET"
        path = f"/trade-api/v2/portfolio/orders/{order_id}"
        headers = self.auth.create_headers(method, path)

        response = requests.get(self.state.rest_base_url + path, headers=headers)
        response.raise_for_status()
        order_data = response.json().get("order", {})

        return Order.from_dict(order_data)



if __name__ == "__main__":
    state = State()
    api = KalshiRestClient(state)

    print(api.get_markets(event_ticker="BTCMAX100-24"))
