from typing import Dict
import requests

from common.state import State
from kalshi.authentication import Authenticator


class KalshiRestClient:

    def __init__(self, state: State, auth: Authenticator) -> None:
        self.state = state
        self.auth = auth
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

    def get_events(self):
        raise NotImplementedError

    def get_event(self, event_ticker: str):
        method = "GET"
        path = f"/trade-api/v2/events/{event_ticker}"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)

    def get_market_trades(self, ticker: str, fetch_all: bool = False):
        path = "/trade-api/v2/markets/trades"

        params = {
            "ticker": ticker,
        }

        results = []
        next_cursor = None

        while True:
            if next_cursor:
                params["cursor"] = next_cursor

            response = requests.get(self.state.rest_base_url + path, params=params)
            response.raise_for_status()

            data = response.json()

            if "trades" in data:
                results.extend(data["trades"])
            else: 
                print("No trades data found in the response")

            next_cursor = data.get("cursor")

            if not fetch_all or not next_cursor:
                break

        return results

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
        method = "GET"
        path = "/trade-api/v2/portfolio/balance"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)
