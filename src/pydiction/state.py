import asyncio
import os
from typing import Dict, List
from dotenv import load_dotenv

from pydiction.utils import load_from_yaml


REFRESH_PERIOD = 10.0  # Refresh period for config refresh in Pydiction


class State:
    load_dotenv()
    CONFIGURATION_PATH = "config.yaml"
    TICKERS_PATH = "tickers.yaml"

    def __init__(self) -> None:
        self.email = os.getenv("KALSHI_EMAIL")
        self.password = os.getenv("KALSHI_PASSWORD")
        self.access_key = os.getenv("KALSHI_ACCESS_KEY")
        self.private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")

        # Check for email and password
        if self.email is None:
            raise ValueError("Environment variable KALSHI_EMAIL is not set or is None")
        if self.password is None:
            raise ValueError(
                "Environment variable KALSHI_PASSWORD is not set or is None"
            )

        # Check if either access_key or private_key_path is None
        if self.access_key is None:
            raise ValueError(
                "Environment variable KALSHI_ACCESS_KEY is not set or is None"
            )
        if self.private_key_path is None:
            raise ValueError(
                "Environment variable KALSHI_PRIVATE_KEY_PATH is not set or is None"
            )

        # Check if either yaml path is invalid or None
        if not self.CONFIGURATION_PATH:
            raise ValueError("Please check that you have a valid `config.yaml` file")
        if not self.TICKERS_PATH:
            raise ValueError("Please check that you have a valid `tickers.yaml` file")

        self._initialize()

    def _load(self, config: Dict, tickers: Dict, refresh: bool = False) -> None:
        if not refresh:
            self.exchange = config["exchange"]
            self.rest_base_url = config["rest_base_url"]
            self.ws_base_url = config["ws_base_url"]
            self.tickers: List[str] = tickers["market_tickers"]

        # eventually, load strategy related params below?

    def _initialize(self) -> None:
        """
        Loads the initial configuration and tickers from their respective yaml files.
        """
        config = load_from_yaml(self.CONFIGURATION_PATH)
        tickers = load_from_yaml(self.TICKERS_PATH)
        self._load(config, tickers)

    async def refresh(self) -> None:
        """
        Refreshes the CONFIGURATION and TICKERS from their YAML files.
        """
        while True:
            await asyncio.sleep(REFRESH_PERIOD)

            # Load yamls
            config = load_from_yaml(self.CONFIGURATION_PATH)
            tickers = load_from_yaml(self.TICKERS_PATH)

            # call load again
            self._load(config, tickers)
