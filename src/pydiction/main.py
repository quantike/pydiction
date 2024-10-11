import asyncio
from typing import Dict, List
import websockets
import json
import requests
import datetime
import os
import yaml
import logging
import signal

from dotenv import load_dotenv

from pydiction.db import convert_levels_to_string
from pydiction.book import Orderbook


# Load environment variables from .env (check sample.env for required variables)
load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
WEBSOCKET_BASE_URL = "trading-api"

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

# Global variable for graceful shutdown
stop_event = asyncio.Event()


# Function to handle graceful shutdown
def signal_handler(sig, frame):
    logging.info("Gracefully shutting down...")
    stop_event.set()


# Logs in to exchange via email + password, returns the session token
def get_kalshi_api_token(email, password):
    url = f"https://{WEBSOCKET_BASE_URL}.kalshi.com/trade-api/v2/login"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
    }
    data = json.dumps({"email": email, "password": password})
    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        logging.info("Logged in to Kalshi Exchange")
    else:
        raise Exception("Failed to log in: " + response.text)

    return response.json()["token"]


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
    with open("snapshot.json", "a") as f:
        json.dump(snapshot, f)
        f.write("\n")


# Save deltas as json (every ~100 updates or on termination)
def save_deltas(deltas: List[Dict]) -> None:
    if deltas: 
        with open("deltas.json", "a") as f:
            for delta in deltas:
                json.dump(delta, f)
                f.write("\n")

        deltas.clear()


# # Orderbook updates
async def update_handler(queue: asyncio.Queue, orderbook: Orderbook, deltas: List[Dict]) -> None:
    while True:
        # If we encounter a stop signal, and there's nothing in the queue we can exit
        if stop_event.is_set() and not queue.qsize():
            break

        message = await queue.get()

        # Update the Orderbook by passing the message 
        orderbook.process(message)
        
        timestamp = int(
            datetime.datetime.now(datetime.timezone.utc).timestamp()
        )  # Get current UTC timestamp as integer

        # Always save snapshots immediately (since they are rare)
        match message["type"]:
            # Handle snapshot
            case "orderbook_snapshot":
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

            # Handle delta
            case "orderbook_delta":
                msg = message["msg"]

                deltas.append({
                    "sid": message["sid"],
                    "seq": message["seq"],
                    "market_ticker": msg["market_ticker"],
                    "price": msg["price"],
                    "delta": msg["delta"],
                    "side": 1 if msg["side"] == "yes" else 0,
                    "timestamp": timestamp,
                })

                if len(deltas) >= 100:
                    save_deltas(deltas)

            # Handle error
            case "error":
                logging.error(f"Code {message["msg"]["code"]}: '{message["msg"]["msg"]}'")

        # Task completed
        queue.task_done()

    # Save any remaining deltas on shutdown 
    save_deltas(deltas)


async def websocket_listener(api_token: str, queue: asyncio.Queue, tickers_filename: str) -> None:
    headers = {"Authorization": f"Bearer {api_token}"}
    tickers = load_market_tickers(tickers_filename)

    async with websockets.connect(
        f"wss://{WEBSOCKET_BASE_URL}.kalshi.com/trade-api/v2",
        extra_headers=headers,
    ) as websocket:
        logging.info(f"Connected to Exchange WebSocket on `{WEBSOCKET_BASE_URL}`")

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
        asyncio.create_task(
            check_for_yaml_updates(websocket, subscription_message, tickers_filename)
        )

        while True: 
            try:
                data = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                await queue.put(json.loads(data))
            except asyncio.TimeoutError:
                continue
            except websockets.ConnectionClosed:
                logging.warning("WebSocket connection closed")
                break


# Main function to run the coroutines
async def main(api_token, market_tickers_file):
    queue = asyncio.Queue()
    orderbook = Orderbook(bids=[], asks=[])
    deltas = []

    await asyncio.gather(
        websocket_listener(api_token, queue, market_tickers_file),
        update_handler(queue, orderbook, deltas)
    )


if __name__ == "__main__":
    # Load environment variables and get API token
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")
    api_token = get_kalshi_api_token(EMAIL, PASSWORD)
    market_tickers_file = "tickers.yaml"

    # Handle signals for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main(api_token, market_tickers_file))
    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        logging.info("Program terminated.")
