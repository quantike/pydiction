# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "loguru",
#     "requests",
# ]
# ///
from packages.kalshi.src.kalshi.rest import KalshiRestClient
from packages.common.src.common.state import State

state = State()
api = KalshiRestClient(state)

api.get_markets(series_ticker='KXBTC')
