import json
import time
import websockets
import asyncio

from typing import Callable, Dict, List, Optional, Set
from collections import namedtuple

from pydiction.state import State
from pydiction.auth import Authenticator


Subscription = namedtuple(
    "Subscription", ["channels", "tickers", "created_ts", "updated_ts", "active"]
)


async def websocket_factory(uri: str, extra_headers: Optional[Dict[str, str]]):
    """Factory function that creates new websocket connections."""
    try:
        websocket = await websockets.connect(uri, extra_headers=extra_headers)
        print(f"connected to ws at {uri}")
        return websocket
    except Exception as e:
        print(f"failed to connect to websocket at {uri} with {e}")
        raise


class KalshiWs:
    def __init__(
        self, state: State, auth: Authenticator, websocket_factory: Callable
    ) -> None:
        self.state = state
        self.auth = auth
        self.websocket_factory = websocket_factory
        self.subscriptions: Dict[int, Subscription] = {}
        self.pending_unsubscriptions: Set = set()
        self._id_counter = 0

    async def connect(self):
        headers = self.auth.get_auth_headers_ws()
        self.websocket: websockets.WebSocketClientProtocol = (
            await self.websocket_factory(self.state.ws_uri, extra_headers=headers)
        )

        # Start listening for messages from the server
        asyncio.create_task(self.listen())

    async def _reconnect(self):
        """Close the connection and attempt to re-connect periodically."""
        await self.websocket.close()
        print("Reconnecting...")

        while True:
            try:
                await self.connect()
                print("Reconnection successful")
                await self.resubscribe_all()
                break
            except Exception as e:
                print(
                    f"Reconnect failed: {e}, retrying in {self.state.reconnection_interval}s..."
                )
                await asyncio.sleep(self.state.reconnection_interval)

    def generate_subscription_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    async def add_subscription(self, channels: List[str], all_markets: bool = False):
        subscription_id = self.generate_subscription_id()
        subscription = Subscription(
            channels=channels,
            tickers=self.state.tickers if not all_markets else ["all_markets"],
            created_ts=time.time(),
            updated_ts=time.time(),
            active=False,
        )

        subscription_message = {
            "id": subscription_id,
            "cmd": "subscribe",
            "params": {
                "channels": channels,
            },
        }

        if not all_markets:
            # If we are not in all_markets mode, update subscription_message with tickers from state
            subscription_message["params"]["market_tickers"] = self.state.tickers

        await self.websocket.send(json.dumps(subscription_message))

        # Update the subscription locally
        self.subscriptions[subscription_id] = subscription
        self.subscriptions[subscription_id] = subscription._replace(
            updated_ts=time.time(), active=True
        )

        return subscription_id

    async def _await_confirmation(self, subscription_id: int):
        """Wait for confirmation within a pre-defined window, else reconnect."""
        await asyncio.sleep(self.state.confirmation_timeout)
        if subscription_id in self.subscriptions:
            print(f"Subscription {subscription_id} not confirmed, reconnecting...")
            await self._reconnect()

    async def update_subscription(
        self, subscription_id: int, updated_tickers: List[str]
    ):
        """
        Updates a subscription by adding or deleting tickers from it. Infers the correct action.

        - Detects tickers to add by: `tickers_to_add = updated_tickers - current_tickers`
        - Detects tickers to delete by: `tickers_to_delete = current_tickers - updated_tickers`

        Will always update additions before deletions. We assume an addition has higher time priority than a deletion.
        """
        if subscription_id not in self.subscriptions:
            # Exit early
            return []

        subscription = self.subscriptions[subscription_id]
        current_tickers = set(subscription.tickers)
        new_tickers = set(updated_tickers)

        # Determine actions to perform
        tickers_to_add = new_tickers - current_tickers
        tickers_to_delete = current_tickers - new_tickers

        actions_performed = []

        # Create and send addition messages, if any
        if tickers_to_add:
            add_message = {
                "id": self.generate_subscription_id(),
                "cmd": "update_subscription",
                "params": {
                    "sids": [
                        subscription_id
                    ],  # presently, support single subscription updates
                    "market_tickers": list(tickers_to_add),
                    "action": "add_markets",
                },
            }

            # TODO: Actually send the add_message to the ws and handle success/failure
            await self.websocket.send(json.dumps(add_message))

            actions_performed.append("add_markets")

        # Create and send deletion messages, if any
        if tickers_to_delete:
            delete_message = {
                "id": self.generate_subscription_id(),
                "cmd": "update_subscription",
                "params": {
                    "sids": [
                        subscription_id
                    ],  # presently, support single subscription updates
                    "market_tickers": list(tickers_to_delete),
                    "action": "delete_markets",
                },
            }

            # TODO: Actually send the delete_message to the ws and handle success/failure
            await self.websocket.send(json.dumps(delete_message))

            actions_performed.append("delete_markets")

        # Update the subscription locally
        self.subscriptions[subscription_id] = subscription._replace(
            tickers=list(new_tickers), updated_ts=time.time()
        )

        return actions_performed

    async def unsubscribe(self, subscription_ids: List[int]):
        """Unsubscribe from one or more subscriptions by their subscription ID."""
        valid_subscription_ids = [
            subscription_id
            for subscription_id in subscription_ids
            if subscription_id in self.subscriptions
        ]

        if valid_subscription_ids:
            # Mark the valid sids as pending
            self.pending_unsubscriptions.update(valid_subscription_ids)

            # NOTE: We do not apply a unique id to this message since it will make the subscription_id diverge
            # from the id that we track locally in self.subscriptions
            unsubscribe_message = {
                "cmd": "unsubscribe",
                "params": {"sids": valid_subscription_ids},
            }

            await self.websocket.send(json.dumps(unsubscribe_message))

            # Update subscriptions locally
            for subscription_id in valid_subscription_ids:
                self.subscriptions.pop(subscription_id)

        # TODO: we should return the successfull unsubscribes only
        return valid_subscription_ids

    async def _handle_forced_unsubscription(self, subscription_id: int):
        """Attemps to re-subscribe if the server sends an unsubscribe event."""
        # Only handle forced unsubscription if it was unintentional. We check this by making sure
        # that the subscription_id has not been added to our pending unsubscription set.
        if (
            subscription_id in self.subscriptions
            and subscription_id not in self.pending_unsubscriptions
        ):
            subscription = self.subscriptions[subscription_id]
            print(
                f"Forced unsubscription detected for SID: {subscription_id}, attempting re-subscribe..."
            )
            await self.add_subscription(channels=subscription.channels)
        elif subscription_id in self.pending_unsubscriptions:
            # Remove subscription_id from pending since it is now handled
            self.pending_unsubscriptions.remove(subscription_id)

    async def resubscribe_all(self):
        """
        Re-subscribes to all active connections after reconnecting.
        """
        for subscription_id, subscription in self.subscriptions.items():
            if subscription.active:
                resubscription_message = {
                    "id": subscription_id,
                    "cmd": "subscribe",
                    "params": {
                        "channels": subscription.channels,
                        "market_tickers": subscription.tickers,
                    },
                }

                await self.websocket.send(json.dumps(resubscription_message))

                # Update subscriptions locally
                # NOTE: The logic in only updating the `updated_ts` is that we might want to know just
                # how long we've been listening to a subscription via the `created_ts`.
                self.subscriptions[subscription_id] = subscription._replace(
                    updated_ts=time.time()
                )

    async def monitor_connection_health(self) -> None:
        """Monitors the connection's health and reconnects if the health has degraded."""
        while True:
            await asyncio.sleep(10.0)  # waits 10 seconds then checks
            try:
                pong = await self.websocket.ping()
                await pong
            except Exception:
                print("Connection health deteriorated, reconnecting...")
                await self._reconnect()

    async def listen(self):
        """Listen for incoming messages from the WebSocket server."""
        try:
            async for message in self.websocket:
                await self.handle_message(json.loads(message))
        except websockets.ConnectionClosed:
            print("Connection closed during listen, reconnecting...")
            await self._reconnect()

    async def handle_message(self, message: Dict):
        """Handles messages received from the server."""
        print(f"handler rx: {message}")
        match message.get("type"):
            # Handles subscriptions
            case "subscribed":
                subscription_id = message.get("id")
                if subscription_id is not None:
                    print(message)
            # Handles un-subcriptions
            case "unsubscribed":
                subscription_id = message.get("sid")
                if subscription_id is not None:
                    await self._handle_forced_unsubscription(subscription_id)
