from typing import Any, Dict, List, Optional
import requests

from common.state import State
from kalshi.authentication import Authenticator


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
        method = "GET"
        path = "/trade-api/v2/markets"
        headers = self.auth.create_headers(method, path)

        # HACK: Optional construction of params from function arguments
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
            return self._deep_fetch_(
                path, params=params, headers=headers, key="markets"
            )

        # Single fetch if fetch_all is false
        response = requests.get(
            self.state.rest_base_url + path, params=params, headers=headers
        )
        response.raise_for_status()
        data = response.json()

        return data.get("markets", [])

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

        return requests.get(self.state.rest_base_url + path, headers=headers)

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

    def get_exchange_schedule(self):
        """
        Requests the exchange schedule.

        Returns:
            Response: The HTTP response object containing the exchange schedule.
        """
        method = "GET"
        path = "/trade-api/v2/exchange/schedule"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)

    def get_exchange_status(self):
        """
        Requests the current exchange status.

        WARNING: This is an undocumented endpoint I happened upon.

        Returns:
            Response: The HTTP response object containing the exchange status.
        """
        method = "GET"
        path = "/trade-api/v2/exchange/status"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)

    def get_exchange_announcements(self):
        """
        Requests exchange announcements, if any.

        Returns:
            Response: The HTTP response object containing exchange announcements.
        """
        method = "GET"
        path = "/trade-api/v2/exchange/announcements"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)

    def get_portfolio_balance(self):
        """
        Requests the portfolio balance for a logged-in user.

        Returns:
            Response: The HTTP response object containing the portfolio balance details.

        Raises:
            Exception: If the user is not logged in.
        """
        if not self.is_connected:
            raise Exception("User not logged in")

        method = "GET"
        path = "/trade-api/v2/portfolio/balance"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)

    def get_portfolio_fills(self, ticker: str, fetch_all: bool = False):
        """
        Retrieves a list of fills for a given portfolio ticker.

        Args:
            ticker (str): The ticker to fetch fills for.
            fetch_all (bool): Whether to fetch all pages of results.

        Returns:
            List[Dict[str, Any]]: A list of fill dictionaries.

        Raises:
            Exception: If the user is not logged in.
        """
        if not self.is_connected:
            raise Exception("User not logged in")

        path = "/trade-api/v2/portfolio/fills"
        params = {"ticker": ticker}

        if fetch_all:
            return self._deep_fetch_(path, params=params, key="fills")

        # Single request if fetch_all is False
        headers = self.auth.create_headers("GET", path)
        response = requests.get(
            self.state.rest_base_url + path, headers=headers, params=params
        )
        response.raise_for_status()
        data = response.json()

        return data.get("fills", [])
