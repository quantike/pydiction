import requests

from pydiction.auth import Authenticator
from pydiction.state import State


class KalshiClient: 

    def __init__(self, state: State, auth: Authenticator) -> None:
        self.state = state
        self.auth = auth
        self.token = self.auth.get_auth_headers_rest(self.state.rest_base_url)

    def get_exchange_schedule(self):
        method = "GET"
        path = "/exchange/schedule"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)

    def get_exchange_status(self):
        """
        Requests the current exchange status. 

        WARNING: This is an undocumented endpoint I happened upon.
        """
        method = "GET"
        path = "/exchange/status"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)
    def get_exchange_announcements(self):
        method = "GET"
        path = "/exchange/announcements"

        headers = self.auth.create_headers(method, path)

        return requests.get(self.state.rest_base_url + path, headers=headers)
