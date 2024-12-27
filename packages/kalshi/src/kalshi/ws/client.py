import asyncio
import json
import time
from typing import Dict, List, Set

import websockets
from common.state import State
from kalshi.authentication import Authenticator
from kalshi.ws.pool import WsPool
from kalshi.ws.handler import KalshiMessageHandler
from kalshi.ws.subscription import Subscription
from loguru import logger


class KalshiWsClient:
    def __init__(self, state: State) -> None:
        self.state = state
        self.auth = Authenticator(self.state)
        self.subscriptions: Dict[int, Subscription] = {}
        self.pending_unsubscriptions: Set = set()
        self._id_counter = 0

        # Set up message handler for message dispatch
        self.handler = KalshiMessageHandler()

        # Set up the WebSocket pool for connection cycling and monitoring
        self.pool: WsPool = WsPool(
            state=self.state,
            n_connections=5,
        )

    async def start(self):
        await self._connect_()
        assert self.websocket is not None
        logger.info(f"Starting client to {self.websocket.remote_address}")

    async def end(self):
        await self._disconnect_()
        logger.critical("Ending client")

    async def _connect_(self):
        await self.pool.run()
        self.websocket = self.pool.connection

        # Start listening for messages from the server
        asyncio.create_task(self.listen())

    async def _disconnect_(self):
        if self.websocket:
            await self.websocket.close()
            logger.critical(f"Websocket connection disconnected from {self.websocket.remote_address}")
            self.websocket = None

    async def _reconnect_(self):
        """Close the connection and attempt to re-connect periodically."""
        assert self.websocket is not None
        await self.websocket.close()
        logger.info("attempting reconnect...")

        while True:
            try:
                await self._connect_()
                logger.success("Reconnection successful")
                await self.resubscribe_all()
                break
            except Exception as e:
                logger.error(
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

        assert self.websocket is not None
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
            logger.error(
                f"Subscription {subscription_id} not confirmed, reconnecting..."
            )
            await self._reconnect_()

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
            assert self.websocket is not None
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
            assert self.websocket is not None
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

            assert self.websocket is not None
            await self.websocket.send(json.dumps(unsubscribe_message))

            # Update subscriptions locally
            for subscription_id in valid_subscription_ids:
                self.subscriptions.pop(subscription_id)

        # TODO: we should return the successfull unsubscribes only
        return valid_subscription_ids

    async def _handle_forced_unsubscription_(self, subscription_id: int):
        """Attemps to re-subscribe if the server sends an unsubscribe event."""
        # Only handle forced unsubscription if it was unintentional. We check this by making sure
        # that the subscription_id has not been added to our pending unsubscription set.
        if (
            subscription_id in self.subscriptions
            and subscription_id not in self.pending_unsubscriptions
        ):
            subscription = self.subscriptions[subscription_id]
            logger.error(
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
    
                assert self.websocket is not None
                await self.websocket.send(json.dumps(resubscription_message))

                # Update subscriptions locally
                # NOTE: The logic in only updating the `updated_ts` is that we might want to know just
                # how long we've been listening to a subscription via the `created_ts`.
                self.subscriptions[subscription_id] = subscription._replace(
                    updated_ts=time.time()
                )

    async def listen(self):
        """Listen for incoming messages from the WebSocket server."""
        try:
            assert self.websocket is not None
            async for message in self.websocket:
                await self.handle_message(json.loads(message))
        except websockets.ConnectionClosed:
            logger.error("Connection closed during listen, reconnecting...")
            await self._reconnect_()

    async def handle_message(self, message: Dict):
        """Handles messages received from the server."""
        match message.get("type"):
            # Handles subscriptions
            case "subscribed":
                subscription_id = message.get("id")
                if subscription_id is not None:
                    logger.info(
                        f"subscription created to channel: {message["msg"]["channel"]}"
                    )
            # Handles un-subcriptions
            case "unsubscribed":
                subscription_id = message.get("sid")
                if subscription_id is not None:
                    await self._handle_forced_unsubscription_(subscription_id)
            # Handles subscription updates
            case "ok":
                subscription_id = message.get("id")
                if subscription_id is not None:
                    logger.info(
                        f"subscription(s) updated with ticker(s): {message["market_tickers"]}"
                    )
            # Handles errors by logging the code and message
            case "error":
                subscription_id = message.get("id")
                if subscription_id is not None:
                    logger.error(f"error received: {message["msg"]}")
            case _:
                self.handler.handle_message(message)
