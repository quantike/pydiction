import asyncio
from typing import Dict, List
import websockets
import json
import datetime
import os
import yaml
import logging
import signal

from dotenv import load_dotenv

from pydiction.db import convert_levels_to_string
from pydiction.book import Orderbook
from pydiction.auth import KalshiAPI


# Load environment variables from .env (check sample.env for required variables)
load_dotenv()

EMAIL = os.getenv("KALSHI_EMAIL")
PASSWORD = os.getenv("KALSHI_PASSWORD")
API_KEY = os.getenv("KALSHI_ACCESS_KEY")
BASE_URL = "trading-api"

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

# Global variable for graceful shutdown
stop_event = asyncio.Event()


# Create instance of the Kalshi API
kalshi_api = KalshiAPI()


# Function to handle graceful shutdown
def signal_handler(sig, frame):
    logging.info("Gracefully shutting down...")
    stop_event.set()


# Function to load latest market tickers from a YAML file
def load_market_tickers(file_path: str) -> List:
    with open(file_path, "r") as file:
        config = yaml.safe_load(file)

    return config["market_tickers"]


# Function to periodically check for YAML file updates
async def check_for_yaml_updates(websocket, subscription_message, market_tickers_file):
    last_modified_time = os.path.getmtime(market_tickers_file)

    while not stop_event.is_set():
        await asyncio.sleep(10)  # Check every 10 seconds

        current_modified_time = os.path.getmtime(market_tickers_file)
        if current_modified_time > last_modified_time:
            logging.info("Market tickers YAML file updated. Reloading...")
            market_tickers = load_market_tickers(market_tickers_file)
            last_modified_time = current_modified_time

            # Update the market tickers in the subscription message
            subscription_message["params"]["market_tickers"] = market_tickers

            # Resubscribe with updated market tickers
            await websocket.send(json.dumps(subscription_message))
            logging.info(f"Resubscribed to new market tickers: {market_tickers}")


# Save snapshots as json
def save_snapshot(snapshot: Dict) -> None:
    with open("data/snapshot.json", "a") as f:
        json.dump(snapshot, f)
        f.write("\n")


# Save deltas as json (every ~100 updates or on termination)
def save_deltas(deltas: List[Dict]) -> None:
    if deltas:
        with open("data/deltas.json", "a") as f:
            for delta in deltas:
                json.dump(delta, f)
                f.write("\n")

        deltas.clear()


async def websocket_listener(
    kalshi_api: KalshiAPI, queue: asyncio.Queue, tickers_filename: str
) -> None:
    headers = kalshi_api.websocket_auth_headers()
    tickers = load_market_tickers(tickers_filename)

    retry_sec = 1.0

    while not stop_event.is_set():
        try:
            async with websockets.connect(
                "wss://trading-api.kalshi.com/trade-api/ws/v2",
                extra_headers=headers,
                ping_interval=10,  # Adjust the ping interval
            ) as websocket:
                logging.info(f"Connected to Exchange WebSocket on `{BASE_URL}`")

                # Send subscription message
                subscription_message = {
                    "id": 1,  # Sequential command ID
                    "cmd": "subscribe",
                    "params": {
                        "channels": ["orderbook_delta"],
                        "market_tickers": tickers,
                    },
                }

                await websocket.send(json.dumps(subscription_message))
                logging.info(f"Subscribing to 'orderbook_delta' channel for {tickers}")

                # Start background task that will check for YAML updates periodically
                _yaml_task = asyncio.create_task(
                    check_for_yaml_updates(
                        websocket, subscription_message, tickers_filename
                    )
                )

                while not stop_event.is_set():
                    try:
                        data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        await queue.put(json.loads(data))
                    except asyncio.TimeoutError:
                        continue
                    except websockets.ConnectionClosed as e:
                        logging.warning(
                            f"WebSocket connection closed: {e.code} - {e.reason}"
                        )
                        if e.code == 1006:
                            logging.warning(
                                "Abnormal closure (1006), attempting to reconnect..."
                            )
                        break

        except Exception as e:
            logging.error(f"WebSocket error: {e}")
            await asyncio.sleep(retry_sec)  # Wait before retrying
        finally:
            logging.info("Attempting to reconnect...")
            await asyncio.sleep(retry_sec)  # Wait before attempting to reconnect


async def update_handler(
    queue: asyncio.Queue, orderbook: Orderbook, deltas: List[Dict]
) -> None:
    while not stop_event.is_set() or not queue.empty():
        try:
            message = await asyncio.wait_for(queue.get(), timeout=5.0)
        except asyncio.TimeoutError:
            continue

        if message:
            # Process the orderbook message as usual
            orderbook.process(message)

            timestamp = int(
                datetime.datetime.now(datetime.timezone.utc).timestamp()
            )  # Get current UTC timestamp as integer

            # Handle snapshot and delta as before
            if message["type"] == "orderbook_snapshot":
                msg = message["msg"]
                snapshot = {
                    "sid": message["sid"],
                    "seq": message["seq"],
                    "market_ticker": msg["market_ticker"],
                    "yes": convert_levels_to_string(msg["yes"]),
                    "no": convert_levels_to_string(msg["no"]),
                    "timestamp": timestamp,
                }
                save_snapshot(snapshot)

            elif message["type"] == "orderbook_delta":
                msg = message["msg"]
                deltas.append(
                    {
                        "sid": message["sid"],
                        "seq": message["seq"],
                        "market_ticker": msg["market_ticker"],
                        "price": msg["price"],
                        "delta": msg["delta"],
                        "side": 1 if msg["side"] == "yes" else 0,
                        "timestamp": timestamp,
                    }
                )

                if len(deltas) >= 100:
                    save_deltas(deltas)

        queue.task_done()

    # Save any remaining deltas on shutdown
    save_deltas(deltas)
    logging.info("Exiting update handler...")


async def main(kalshi_api, market_tickers_file):
    queue = asyncio.Queue()
    orderbook = Orderbook(bids=[], asks=[])
    deltas = []

    listener_task = asyncio.create_task(
        websocket_listener(kalshi_api, queue, market_tickers_file)
    )
    handler_task = asyncio.create_task(update_handler(queue, orderbook, deltas))

    await asyncio.wait([listener_task, handler_task], return_when=asyncio.ALL_COMPLETED)


if __name__ == "__main__":
    # Load environment variables and get API token
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")
    kalshi_api = KalshiAPI()
    market_tickers_file = "tickers.yaml"

    # Handle signals for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main(kalshi_api, market_tickers_file))
    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        logging.info("Program terminated.")
