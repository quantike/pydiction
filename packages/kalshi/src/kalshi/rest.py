from typing import Any, Dict, List, Optional
import requests

from common.state import State
from kalshi.authentication import Authenticator


class KalshiRestClient:
    def __init__(self, state: State) -> None:
        self.state = state
        self.auth = Authenticator(self.state)
        self.is_connected = self._connect_()

    def _connect_(self) -> bool:
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

        Attributes:
            path (str): The API endpoint path to fetch from.
            key (str): The key in the JSON response containing the list of items to fetch.
            params (dict): Optional dictionary of query parameters.
            headers (dict): Optional dictionary of headers.
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
        path = f"/trade-api/v2/series/{series_ticker}"

        return requests.get(self.state.rest_base_url + path)

    def get_events(
        self,
        series_ticker: Optional[str] = None,
        status: Optional[str] = None,
        with_nested_markets: bool = False,
        fetch_all: bool = False,
    ):
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
        method = "GET"
        path = f"/trade-api/v2/markets/{market_ticker}"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)

    def get_market_trades(self, ticker: str, fetch_all: bool = False):
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
        """
        method = "GET"
        path = "/trade-api/v2/exchange/schedule"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)

    def get_exchange_status(self):
        """
        Requests the current exchange status.

        WARNING: This is an undocumented endpoint I happened upon.
        """
        method = "GET"
        path = "/trade-api/v2/exchange/status"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)

    def get_exchange_announcements(self):
        """
        Requests exchange announcements, if any.
        """
        method = "GET"
        path = "/trade-api/v2/exchange/announcements"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)

    def get_portfolio_balance(self):
        """
        Requests the portfolio balance for a logged-in user. Returns the balance in dollar cents,
        and the available payout in dollar cents.
        """
        if not self.is_connected:
            raise Exception("User not logged in")

        method = "GET"
        path = "/trade-api/v2/portfolio/balance"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)

    def get_portfolio_fills(self, ticker: str, fetch_all: bool = False):
        """ """
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
