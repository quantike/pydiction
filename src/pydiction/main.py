import asyncio
import websockets
import json
import requests
import datetime
import os
import yaml
import logging
import signal

from dotenv import load_dotenv

from pydiction.db import (
    convert_levels_to_string,
    get_or_create_market_id,
    setup_database,
)


# Load environment variables from .env (check sample.env for required variables)
load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

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
    url = "https://trading-api.kalshi.com/trade-api/v2/login"
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
def load_market_tickers(file_path):
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
            subscription_message['params']['market_tickers'] = market_tickers

            # Resubscribe with updated market tickers
            await websocket.send(json.dumps(subscription_message))
            logging.info(f"Resubscribed to new market tickers: {market_tickers}")


# Connects to the orderbook(s), and streams that data to our sqlite instance
async def connect_and_stream(api_token, conn, market_tickers_file):
    headers = {"Authorization": f"Bearer {api_token}"}

    market_tickers = load_market_tickers(market_tickers_file)

    async with websockets.connect(
        "wss://trading-api.kalshi.com/trade-api/ws/v2",
        extra_headers=headers,
    ) as websocket:
        logging.info("Connected to Kalshi Exchange Websocket feed")

        # Subscription message
        subscription_message = {
            "id": 1,  # Sequential command ID
            "cmd": "subscribe",
            "params": {
                "channels": ["orderbook_delta"],
                "market_tickers": market_tickers,
            },
        }

        await websocket.send(json.dumps(subscription_message))
        logging.info(f"Subscribing to `orderbook` for market tickers: {market_tickers}")

        cursor = conn.cursor()

        # Start a background task to check for YAML updates periodically
        asyncio.create_task(check_for_yaml_updates(websocket, subscription_message, market_tickers_file))

        while not stop_event.is_set():  # Check for stop event
            try:
                data = await asyncio.wait_for(websocket.recv(), timeout=1.0)  # Non-blocking receive
            except asyncio.TimeoutError:
                continue  # Continue on timeout

            json_data = json.loads(data)
            timestamp = int(
                datetime.datetime.now(datetime.timezone.utc).timestamp()
            )  # Get current UTC timestamp as integer

            # Process orderbook snapshot
            if json_data["type"] == "orderbook_snapshot":
                logging.info("snapshot msg rx")

                market_ticker = json_data["msg"]["market_ticker"]
                market_id = json_data["msg"]["market_id"]
                sid = json_data["sid"]
                seq = json_data["seq"]
                yes_levels = convert_levels_to_string(
                    json_data["msg"].get("yes", [])
                )  # Convert "yes" levels to string
                no_levels = convert_levels_to_string(
                    json_data["msg"].get("no", [])
                )  # Convert "no" levels to string

                # Get or create market entry
                market_db_id = get_or_create_market_id(cursor, market_id, market_ticker)

                cursor.execute(
                    """
                    INSERT INTO snapshots (sid, seq, market_id, yes, no, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (sid, seq, market_db_id, yes_levels, no_levels, timestamp),
                )

            # Process orderbook delta
            elif json_data["type"] == "orderbook_delta":
                logging.info("delta msg rx")

                market_ticker = json_data["msg"]["market_ticker"]
                market_id = json_data["msg"]["market_id"]
                sid = json_data["sid"]
                seq = json_data["seq"]
                price = json_data["msg"]["price"]
                delta = json_data["msg"]["delta"]
                side = (
                    1 if json_data["msg"]["side"] == "yes" else 0
                )  # Store side as 1 (yes) or 0 (no)

                # Get or create market entry
                market_db_id = get_or_create_market_id(cursor, market_id, market_ticker)

                cursor.execute(
                    """
                    INSERT INTO deltas (sid, seq, market_id, price, delta, side, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (sid, seq, market_db_id, price, delta, side, timestamp),
                )

            conn.commit()


# Main function to start the process
def main():
    # Handle signals for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signals

    api_token = get_kalshi_api_token(EMAIL, PASSWORD)  # Retrieve API token
    conn = setup_database(enable_wal=True)  # Set up the database
    market_tickers_file = "tickers.yaml"  # Path to the YAML file with market tickers

    try:
        asyncio.run(connect_and_stream(api_token, conn, market_tickers_file))
    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        conn.close()  # Close the SQLite connection when done
        logging.info("Program terminated.")


if __name__ == "__main__":
    main()
